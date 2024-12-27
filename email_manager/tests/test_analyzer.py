from datetime import datetime
from unittest.mock import patch, MagicMock
import unittest
import logging

from anthropic import APIError

from ..models import EmailContent
from ..database.models import EmailCategory, Base
from ..analyzer.analyzer import EmailAnalyzer
from ..analyzer.models import InsufficientCreditsError
from ..logger import get_logger
from ..database.manager import DatabaseManager

# Set log level for all loggers to reduce noise during tests
logging.getLogger('email_manager').setLevel(logging.WARNING)

class TestEmailAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.claude_api = MagicMock()
        self.db_manager = DatabaseManager()
        self.email_analyzer = EmailAnalyzer(self.claude_api, self.db_manager)
        
        # Initialize database tables
        with self.db_manager.get_session() as session:
            Base.metadata.create_all(session.get_bind())

        # Create a test email
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
    def test_save_and_summarize_categorization(self, mock_anthropic_class):
        """Test categorization of emails that should be saved and summarized."""
        # Mock Claude API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"category": "save_and_summarize", "confidence": 0.95, "reasoning": "Contains important technical information"}')]
        self.claude_api.messages.create.return_value = mock_response

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.SAVE_AND_SUMMARIZE)
        self.assertGreater(result.confidence, 0.9)
        self.assertIsNotNone(result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_non_essential_email_categorization(self, mock_anthropic_class):
        """Test categorization of non-essential emails."""
        # Mock Claude API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"category": "non_essential", "confidence": 0.95, "reasoning": "Marketing newsletter"}')]
        self.claude_api.messages.create.return_value = mock_response

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.NON_ESSENTIAL)
        self.assertGreater(result.confidence, 0.9)
        self.assertIsNotNone(result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_important_email_categorization(self, mock_anthropic_class):
        """Test categorization of important emails."""
        # Mock Claude API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"category": "important", "confidence": 0.95, "reasoning": "Urgent business matter"}')]
        self.claude_api.messages.create.return_value = mock_response

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertGreater(result.confidence, 0.9)
        self.assertIsNotNone(result.reasoning)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_insufficient_credits_handling(self, mock_anthropic_class):
        """Test handling of insufficient credits error."""
        # Create mock request for API error
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url = "https://api.anthropic.com/v1/messages"
        
        # Create API error with credit balance message
        error = APIError(
            message="Your credit balance is too low",
            request=mock_request,
            body={"error": {"type": "insufficient_credit", "message": "Your credit balance is too low"}}
        )
        self.claude_api.messages.create.side_effect = error

        # Verify it raises InsufficientCreditsError
        with self.assertRaises(InsufficientCreditsError):
            self.email_analyzer.analyze_email(self.test_email)

        # Verify credits_exhausted flag is set
        self.assertTrue(self.email_analyzer._credits_exhausted)

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_invalid_response_handling(self, mock_anthropic_class):
        """Test handling of invalid API responses."""
        # Mock Claude API response with invalid JSON
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='invalid json')]
        self.claude_api.messages.create.return_value = mock_response

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.error_message, "Failed to parse response as JSON")
        self.assertEqual(result.reasoning, "Error occured.")

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_api_error_handling(self, mock_anthropic_class):
        """Test handling of API errors."""
        # Mock API error with request
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.url = "https://api.anthropic.com/v1/messages"
        
        api_error = APIError(
            message="API Error occurred",
            request=mock_request,
            body={"error": {"type": "api_error", "message": "API Error occurred"}}
        )
        self.claude_api.messages.create.side_effect = api_error

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.error_message, str(api_error))
        self.assertEqual(result.reasoning, "API Error occurred during analysis")

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_general_error_handling(self, mock_anthropic_class):
        """Test handling of general errors."""
        # Mock general error
        self.claude_api.messages.create.side_effect = Exception("Some error")

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.error_message, "Error during analysis: Some error")
        self.assertEqual(result.reasoning, "General error occurred during analysis")

    @patch('email_manager.analyzer.analyzer.Anthropic')
    def test_invalid_json_response(self, mock_anthropic_class):
        """Test handling of invalid JSON response."""
        # Mock Claude API response with invalid JSON
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='invalid json')]
        self.claude_api.messages.create.return_value = mock_response

        result = self.email_analyzer.analyze_email(self.test_email)
        self.assertEqual(result.category, EmailCategory.IMPORTANT)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.error_message, "Failed to parse response as JSON")
        self.assertEqual(result.reasoning, "Error occured.")

if __name__ == '__main__':
    unittest.main()
