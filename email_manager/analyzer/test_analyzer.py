from datetime import datetime
from unittest.mock import patch, MagicMock
import unittest

from anthropic import APIError
from ..models import EmailContent
from ..database.models import EmailCategory
from .analyzer import EmailAnalyzer
from .models import InsufficientCreditsError
from ..logger import get_logger

logger = get_logger(__name__)

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
        
        # Verify the result
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.reasoning, "Urgent business matter")

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_tech_ai_email_categorization(self, mock_anthropic_class):
        """Test categorization of tech/AI emails."""
        # Create mock responses for both the categorization and summary calls
        category_response = MagicMock()
        category_response.content = [
            MagicMock(
                text='{"category": "tech_ai", "confidence": 0.95, "reasoning": "GitHub notification about repository updates and technical changes"}',
                type='text'
            )
        ]
        
        summary_response = MagicMock()
        summary_response.content = [
            MagicMock(
                text='{"summary_points": ["Key update: New feature released", "Action: Review changes by EOD"]}',
                type='text'
            )
        ]
        
        # Set up the mock client to return different responses for each call
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [category_response, summary_response]
        mock_anthropic_class.return_value = mock_client

        # Create analyzer and analyze email
        analyzer = EmailAnalyzer()
        result = analyzer.analyze_email(self.test_email)

        # Verify both API calls were made
        self.assertEqual(mock_client.messages.create.call_count, 2)
        
        # Check first call (categorization)
        first_call = mock_client.messages.create.call_args_list[0]
        self.assertEqual(first_call.kwargs['model'], analyzer.model)
        self.assertEqual(first_call.kwargs['max_tokens'], 1000)
        self.assertIsInstance(first_call.kwargs['messages'], list)
        
        # Check second call (summary)
        second_call = mock_client.messages.create.call_args_list[1]
        self.assertEqual(second_call.kwargs['model'], analyzer.model)
        self.assertEqual(second_call.kwargs['max_tokens'], 1000)
        self.assertIsInstance(second_call.kwargs['messages'], list)
        
        # Verify the result
        self.assertEqual(result.category, EmailCategory.TECH_AI)
        self.assertEqual(result.confidence, 0.95)
        self.assertIn("GitHub notification", result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_non_essential_email_categorization(self, mock_anthropic_class):
        """Test categorization of non-essential emails."""
        # Create a mock response that mimics the Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"category": "non_essential", "confidence": 0.95, "reasoning": "Marketing newsletter about promotional offers"}',
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

        # Verify the mock was called correctly (only once, no summary needed)
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs['model'], analyzer.model)
        self.assertEqual(call_kwargs['max_tokens'], 1000)
        self.assertIsInstance(call_kwargs['messages'], list)
        
        # Verify the result
        self.assertEqual(result.category, EmailCategory.NON_ESSENTIAL)
        self.assertEqual(result.confidence, 0.95)
        self.assertIn("Marketing newsletter", result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_insufficient_credits_error(self, mock_anthropic_class):
        """Test handling of insufficient credits error."""
        # Mock the API to raise an error indicating insufficient credits
        error = APIError(
            message="Your credit balance is too low to make this request",
            request=MagicMock(method="POST", url="https://api.anthropic.com/v1/messages"),
            body={"error": {"type": "insufficient_credit", "message": "Your credit balance is too low"}}
        )
        
        # Set up the mock client to raise the error
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = error
        mock_anthropic_class.return_value = mock_client

        # Test that InsufficientCreditsError is raised
        analyzer = EmailAnalyzer()
        with self.assertRaises(InsufficientCreditsError):
            analyzer.analyze_email(self.test_email)

        # Verify the mock was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs['model'], analyzer.model)
        self.assertEqual(call_kwargs['max_tokens'], 1000)
        self.assertIsInstance(call_kwargs['messages'], list)

if __name__ == '__main__':
    unittest.main()