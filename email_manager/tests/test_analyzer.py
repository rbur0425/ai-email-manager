from datetime import datetime
from unittest.mock import patch, MagicMock
import unittest
import logging

from anthropic import APIError

from ..models import EmailContent
from ..database.models import EmailCategory
from ..analyzer.analyzer import EmailAnalyzer
from ..analyzer.models import InsufficientCreditsError
from ..logger import get_logger

# Set log level for all loggers to reduce noise during tests
logging.getLogger('email_manager').setLevel(logging.WARNING)

class TestEmailAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_email = EmailContent(
            email_id="test123",
            subject="Test Email",
            sender="test@example.com",
            content="This is a test email body",
            received_date=datetime.now()
        )

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_important_email_categorization(self, mock_anthropic_class):
        """Test categorization of important emails."""
        # Create a mock response that mimics the Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"category": "important", "confidence": 0.95, "reasoning": "Urgent business matter"}',
                type='text'
            )
        ]
        
        # Set up the mock client
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        # Create analyzer and analyze email
        analyzer = EmailAnalyzer()
        result = analyzer.analyze_email(self.test_email)

        # Verify the mock was called correctly
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs['model'], analyzer.model)
        self.assertEqual(call_kwargs['max_tokens'], 1000)
        self.assertIsInstance(call_kwargs['messages'], list)

        # Verify result
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertGreater(result.confidence, 0.9)
        self.assertTrue(result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_tech_email_categorization(self, mock_anthropic_class):
        """Test categorization of tech/AI related emails."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"category": "tech_ai", "confidence": 0.85, "reasoning": "Contains AI technology discussion"}',
                type='text'
            )
        ]
        
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        analyzer = EmailAnalyzer()
        result = analyzer.analyze_email(self.test_email)

        # Verify result
        self.assertEqual(result.category, EmailCategory.TECH_AI)
        self.assertGreater(result.confidence, 0.8)
        self.assertTrue(result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_non_essential_email_categorization(self, mock_anthropic_class):
        """Test categorization of non-essential emails."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"category": "non_essential", "confidence": 0.75, "reasoning": "Marketing newsletter"}',
                type='text'
            )
        ]
        
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        analyzer = EmailAnalyzer()
        result = analyzer.analyze_email(self.test_email)

        # Verify result
        self.assertEqual(result.category, EmailCategory.NON_ESSENTIAL)
        self.assertGreater(result.confidence, 0.7)
        self.assertTrue(result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_api_error_handling(self, mock_anthropic_class):
        """Test handling of API errors."""
        # Mock API error
        error = APIError(
            message="API Error",
            request=MagicMock(method="POST", url="https://api.anthropic.com/v1/messages"),
            body={"error": {"type": "api_error", "message": "API Error"}}
        )
        
        # Set up the mock client to raise the error
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = error
        mock_anthropic_class.return_value = mock_client

        analyzer = EmailAnalyzer()
        result = analyzer.analyze_email(self.test_email)
        
        # Verify we got a fallback analysis
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("API Error", result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_insufficient_credits_handling(self, mock_anthropic_class):
        """Test handling of insufficient credits error."""
        # Mock API error that indicates insufficient credits
        error = APIError(
            message="Your credit balance is too low to make this request",
            request=MagicMock(method="POST", url="https://api.anthropic.com/v1/messages"),
            body={"error": {"type": "insufficient_credit", "message": "Your credit balance is too low"}}
        )
        
        # Set up the mock client to raise the error
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = error
        mock_anthropic_class.return_value = mock_client

        analyzer = EmailAnalyzer()
        with self.assertRaises(InsufficientCreditsError):
            analyzer.analyze_email(self.test_email)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_invalid_response_handling(self, mock_anthropic_class):
        """Test handling of invalid API responses."""
        # Create a mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"invalid": "json"',  # Invalid JSON missing closing brace
                type='text'
            )
        ]
        
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        analyzer = EmailAnalyzer()
        result = analyzer.analyze_email(self.test_email)
        
        # Verify we got a fallback analysis
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("Failed to parse response as JSON", result.reasoning)

if __name__ == '__main__':
    unittest.main()
