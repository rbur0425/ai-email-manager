"""
End-to-end test for the Email Manager system.
Testing non-essential, save-and-summarize, important email processing, error handling, batch processing,
edge cases, and infrastructure failures.
"""
import unittest
from datetime import datetime
import pytz
from unittest.mock import MagicMock, patch
import os

from email_manager.database import EmailCategory, DatabaseManager
from email_manager.manager import EmailManager, EmailProcessingError
from email_manager.models import EmailContent, EmailAnalysis

class TestEmailManagerE2E(unittest.TestCase):
    """End-to-end test suite for the Email Manager system."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        # Initialize test database
        db_manager = DatabaseManager(database_name=os.getenv('TEST_DB_NAME', 'email_manager_test'))
        db_manager.create_tables()
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create mock services with all required methods
        self.gmail_service = MagicMock()
        self.email_analyzer = MagicMock()
        self.db_manager = MagicMock()
        
        # Configure db_manager mock with required methods
        self.db_manager.store_deleted_email.return_value = True
        self.db_manager.archive_saved_email.return_value = True
        self.db_manager.add_processing_history.return_value = True
        self.db_manager.engine = MagicMock()  # Mock the database engine
        self.db_manager.SessionLocal = MagicMock()  # Mock the session factory
        
        # Configure gmail service mock
        self.gmail_service.mark_as_read.return_value = True
        self.gmail_service.mark_as_unread.return_value = True
        
        # Create email manager instance
        self.email_manager = EmailManager(
            self.gmail_service,
            self.email_analyzer,
            self.db_manager
        )
        
        # Sample test data
        self.test_email = EmailContent(
            email_id="test123",
            subject="Test Email",
            sender="test@example.com",
            content="This is a test email content",
            received_date=datetime.now(pytz.UTC)
        )
    
    def test_non_essential_email_flow(self):
        """Test complete flow for non-essential email processing."""
        # Setup mock returns
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        self.email_analyzer.analyze_email.return_value = EmailAnalysis(
            category=EmailCategory.NON_ESSENTIAL,
            confidence=0.95,
            reasoning="Advertisement content detected",
            summary=None
        )
        
        # Execute
        self.email_manager.process_unread_emails(batch_size=1)
        
        # Verify flow
        self.gmail_service.get_unread_emails.assert_called_once()
        self.email_analyzer.analyze_email.assert_called_once_with(self.test_email)
        self.db_manager.store_deleted_email.assert_called_once()
        self.gmail_service.move_to_trash.assert_called_once_with(self.test_email.email_id)
        self.db_manager.add_processing_history.assert_called_once()
    
    def test_save_and_summarize_email_flow(self):
        """Test complete flow for emails that should be saved and summarized."""
        # Setup test email
        test_email = EmailContent(
            email_id="test123",
            subject="Project Update",
            sender="test@example.com",
            content="Project content",
            received_date=datetime.now(pytz.UTC)
        )
        
        # Configure Gmail service to return our test email
        self.gmail_service.get_unread_emails.return_value = [test_email]
        
        # Configure successful analysis
        analysis = EmailAnalysis(
            category=EmailCategory.SAVE_AND_SUMMARIZE,
            confidence=0.95,
            reasoning="Important project content detected",
            summary="• Point 1\n• Point 2\n• Point 3"
        )
        self.email_analyzer.analyze_email.return_value = analysis
        
        # Configure successful summary generation
        self.email_analyzer.generate_summary.return_value = analysis.summary
        
        # Configure successful database operations
        self.db_manager.archive_saved_email.return_value = True
        
        # Process the email
        self.email_manager.process_unread_emails(batch_size=1)
        
        # Verify analysis was performed
        self.email_analyzer.analyze_email.assert_called_once_with(test_email)
        
        # Verify summary was generated
        self.email_analyzer.generate_summary.assert_called_once_with(test_email)
        
        # Verify content was archived
        self.db_manager.archive_saved_email.assert_called_once_with(
            email_id=test_email.email_id,
            subject=test_email.subject,
            sender=test_email.sender,
            content=test_email.content,
            summary=analysis.summary,
            received_date=test_email.received_date,
            category=EmailCategory.SAVE_AND_SUMMARIZE
        )
        
        # Verify email was moved to trash after archiving
        self.gmail_service.move_to_trash.assert_called_once_with(test_email.email_id)
        
        # Verify processing history was recorded
        self.db_manager.add_processing_history.assert_called_with(
            email_id=test_email.email_id,
            action="processed",
            category=analysis.category,
            confidence=analysis.confidence,
            success=True,
            reasoning=analysis.reasoning
        )
    
    def test_important_email_flow(self):
        """Test complete flow for important email processing."""
        # Reset mock call counts from previous tests
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Setup mock returns
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        self.email_analyzer.analyze_email.return_value = EmailAnalysis(
            category=EmailCategory.IMPORTANT,
            confidence=0.85,
            reasoning="Important business content detected",
            summary=None
        )
        
        # Execute
        self.email_manager.process_unread_emails(batch_size=1)
        
        # Verify flow
        self.gmail_service.get_unread_emails.assert_called_once()
        self.email_analyzer.analyze_email.assert_called_once_with(self.test_email)
        self.gmail_service.mark_as_read.assert_called_once_with(self.test_email.email_id)
        self.db_manager.add_processing_history.assert_called_once()
        
        # Verify that move_to_trash was NOT called
        self.gmail_service.move_to_trash.assert_not_called()

    def test_error_handling_and_retries(self):
        """Test error handling and retry mechanism."""
        # Reset mock call counts from previous tests
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Setup mock to fail twice then succeed
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        self.email_analyzer.analyze_email.side_effect = [
            Exception("API Error 1"),  # First call fails
            Exception("API Error 2"),  # Second call fails
            EmailAnalysis(  # Third call succeeds
                category=EmailCategory.IMPORTANT,
                confidence=0.85,
                reasoning="Important content",
                summary=None
            )
        ]
        
        # Execute
        with self.assertLogs('email_manager.manager', level='WARNING') as log:
            self.email_manager.process_unread_emails(batch_size=1)
        
        # Verify retry attempts
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 3)
        
        # Verify warning logs for failures
        self.assertTrue(any("API Error 1" in msg for msg in log.output))
        self.assertTrue(any("API Error 2" in msg for msg in log.output))
        
        # Verify final successful processing
        self.gmail_service.mark_as_read.assert_called_once_with(self.test_email.email_id)
        self.db_manager.add_processing_history.assert_called_once()
        
        # Verify that move_to_trash was NOT called (since it's an important email)
        self.gmail_service.move_to_trash.assert_not_called()

    def test_batch_processing(self):
        """Test processing multiple emails of different types in a single batch."""
        # Reset mock call counts from previous tests
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Create test emails
        non_essential_email = EmailContent(
            email_id="ad123",
            subject="Special Offer!",
            sender="marketing@example.com",
            content="Limited time offer!",
            received_date=datetime.now(pytz.UTC)
        )
        
        save_and_summarize_email = EmailContent(
            email_id="save456",
            subject="Project Update",
            sender="test@example.com",
            content="Project content",
            received_date=datetime.now(pytz.UTC)
        )
        
        important_email = EmailContent(
            email_id="imp789",
            subject="Project Status",
            sender="boss@example.com",
            content="Important project update",
            received_date=datetime.now(pytz.UTC)
        )
        
        # Setup mock returns
        self.gmail_service.get_unread_emails.return_value = [
            non_essential_email,
            save_and_summarize_email,
            important_email
        ]
        
        def analyze_email_side_effect(email):
            """Side effect function to return different analysis based on email ID."""
            if email.email_id == "ad123":
                return EmailAnalysis(
                    category=EmailCategory.NON_ESSENTIAL,
                    confidence=0.95,
                    reasoning="Advertisement detected",
                    summary=None
                )
            elif email.email_id == "save456":
                return EmailAnalysis(
                    category=EmailCategory.SAVE_AND_SUMMARIZE,
                    confidence=0.85,
                    reasoning="Project content detected",
                    summary="Summary of large project content"
                )
            else:
                return EmailAnalysis(
                    category=EmailCategory.IMPORTANT,
                    confidence=0.85,
                    reasoning="Important content detected",
                    summary=None
                )
        
        self.email_analyzer.analyze_email.side_effect = analyze_email_side_effect
        
        # Execute
        self.email_manager.process_unread_emails(batch_size=3)
        
        # Verify all emails were analyzed
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 3)
        
        # Verify non-essential email processing
        self.db_manager.store_deleted_email.assert_called_once()
        self.gmail_service.move_to_trash.assert_any_call("ad123")
        
        # Verify save and summarize email processing
        self.db_manager.archive_saved_email.assert_called_once()
        self.gmail_service.move_to_trash.assert_any_call("save456")
        
        # Verify important email processing
        self.gmail_service.mark_as_read.assert_called_once_with("imp789")
        
        # Verify logging for all emails
        self.assertEqual(self.db_manager.add_processing_history.call_count, 3)

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Reset mock call counts from previous tests
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Test case 1: Empty email content
        empty_email = EmailContent(
            email_id="empty123",
            subject="",
            sender="test@example.com",
            content="",
            received_date=datetime.now(pytz.UTC)
        )
        
        # Test case 2: Very large email content
        large_email = EmailContent(
            email_id="large456",
            subject="Large Email" * 100,  # Long subject
            sender="test@example.com",
            content="Large content " * 10000,  # ~100KB of content
            received_date=datetime.now(pytz.UTC)
        )
        
        # Test case 3: Special characters in email
        special_chars_email = EmailContent(
            email_id="special789",
            subject=" Special Characters Test ",
            sender="test@example.com",
            content="Special chars: , , , , , , ",
            received_date=datetime.now(pytz.UTC)
        )
        
        # Test case 4: Invalid format but processable
        invalid_email = EmailContent(
            email_id="invalid101",
            subject=None,  # Invalid subject
            sender="invalid-email-format",  # Invalid sender format
            content=123,  # Wrong type for content
            received_date=datetime.now(pytz.UTC)
        )
        
        test_emails = [empty_email, large_email, special_chars_email, invalid_email]
        self.gmail_service.get_unread_emails.return_value = test_emails
        
        # Configure analyzer to handle each case
        def analyze_email_side_effect(email):
            """Return appropriate analysis based on email type."""
            if email.email_id == "empty123":
                return EmailAnalysis(
                    category=EmailCategory.NON_ESSENTIAL,
                    confidence=0.99,
                    reasoning="Empty content treated as non-essential",
                    summary=None
                )
            elif email.email_id == "large456":
                return EmailAnalysis(
                    category=EmailCategory.SAVE_AND_SUMMARIZE,
                    confidence=0.85,
                    reasoning="Large project content detected",
                    summary="Summary of large project content"
                )
            elif email.email_id == "special789":
                return EmailAnalysis(
                    category=EmailCategory.IMPORTANT,
                    confidence=0.90,
                    reasoning="Important content with special characters",
                    summary=None
                )
            else:  # invalid101
                return EmailAnalysis(
                    category=EmailCategory.NON_ESSENTIAL,
                    confidence=0.70,
                    reasoning="Invalid format treated as non-essential",
                    summary=None
                )
        
        self.email_analyzer.analyze_email.side_effect = analyze_email_side_effect
        
        # Execute with all edge cases
        self.email_manager.process_unread_emails(batch_size=4)
        
        # Verify all emails were processed
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 4)
        
        # Verify empty email was handled
        self.gmail_service.move_to_trash.assert_any_call("empty123")
        
        # Verify large email was processed and stored
        self.db_manager.archive_saved_email.assert_called_once()
        self.gmail_service.move_to_trash.assert_any_call("large456")
        
        # Verify special characters email was marked as important
        self.gmail_service.mark_as_read.assert_called_once_with("special789")
        
        # Verify invalid email was moved to trash
        self.gmail_service.move_to_trash.assert_any_call("invalid101")
        
        # Verify all emails were logged
        self.assertEqual(self.db_manager.add_processing_history.call_count, 4)

    def test_max_retries_exceeded(self):
        """Test behavior when maximum retries are exceeded.
        
        When max retries are exceeded:
        1. The error should be logged
        2. The email should be marked as unread for retry in next batch
        3. The failure should be logged with IMPORTANT category
        4. An EmailProcessingError should be raised
        """
        # Setup
        test_email = EmailContent(
            email_id="test123",
            subject="Test Email",
            sender="test@example.com",
            content="Test content",
            received_date=datetime.now(pytz.UTC)
        )
        
        # Configure mocks
        self.gmail_service.get_unread_emails.return_value = [test_email]
        self.email_analyzer.analyze_email.side_effect = Exception("Persistent error")
        
        # Test
        with self.assertRaises(EmailProcessingError) as context:
            self.email_manager.process_unread_emails(batch_size=1, max_retries=2)
        
        # Verify error message
        error_msg = str(context.exception)
        self.assertIn("Failed to process email after 2 attempts", error_msg)
        
        # Verify retry behavior
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 2)
        
        # Verify failure logging
        self.db_manager.add_processing_history.assert_called_with(
            email_id=test_email.email_id,
            action="failed",
            category=EmailCategory.IMPORTANT,
            confidence=0.0,
            success=False,
            error_message="Persistent error",
            reasoning="Failed to process email"
        )

    def test_database_failures(self):
        """Test handling of database connection failures."""
        # Configure test data
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        self.email_analyzer.analyze_email.return_value = EmailAnalysis(
            category=EmailCategory.SAVE_AND_SUMMARIZE,
            confidence=0.90,
            reasoning="Project content detected",
            summary="Summary of project content"
        )
        
        # Simulate database failures
        self.db_manager.archive_saved_email.return_value = False  # Simulate store failure
        
        # Execute with database failures and verify error handling
        with self.assertLogs('email_manager.manager', level='DEBUG') as log:
            with self.assertRaises(EmailProcessingError) as context:
                self.email_manager.process_unread_emails(batch_size=1, max_retries=1)
            
            # Verify the error message
            error_msg = str(context.exception)
            self.assertIn("Failed to process email after 1 attempts", error_msg)
            self.assertIn("Failed to archive email", error_msg)
            
            # Verify error was logged
            error_logs = [msg for msg in log.output if "ERROR" in msg]
            self.assertTrue(any("Failed to archive email" in msg for msg in error_logs))
            
            # Verify debug logs show the flow
            debug_logs = [msg for msg in log.output if "DEBUG" in msg]
            self.assertTrue(any("Attempting to store saved content" in msg for msg in debug_logs))
            self.assertTrue(any("Store saved content result" in msg for msg in debug_logs))
            
            # Verify attempted database operations
            self.assertEqual(self.db_manager.archive_saved_email.call_count, 1)
            
            # Verify no trash operations were performed (since store failed)
            self.gmail_service.move_to_trash.assert_not_called()

    def test_api_quota_exceeded(self):
        """Test handling of API quota/rate limit exceeded."""
        # Reset mock call counts
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Configure Gmail API to simulate quota exceeded
        quota_error = Exception("Quota exceeded for Gmail API")
        self.gmail_service.get_unread_emails.side_effect = quota_error
        
        # Execute and verify quota handling
        with self.assertLogs('email_manager.manager', level='ERROR') as log:
            with self.assertRaises(EmailProcessingError) as context:
                self.email_manager.process_unread_emails(batch_size=1)
            
            # Verify the error message
            self.assertIn("Quota exceeded", str(context.exception))
        
        # Verify error logging
        self.assertTrue(any("Quota exceeded" in msg for msg in log.output))
        
        # Verify no further processing was attempted
        self.email_analyzer.analyze_email.assert_not_called()
        self.db_manager.archive_saved_email.assert_not_called()
        self.gmail_service.move_to_trash.assert_not_called()

    def test_cleanup_after_processing(self):
        """Test proper cleanup after email processing."""
        # Reset mock call counts
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Create multiple test emails
        test_emails = [
            EmailContent(
                email_id=f"test{i}",
                subject=f"Test {i}",
                sender="test@example.com",
                content=f"Content {i}",
                received_date=datetime.now(pytz.UTC)
            ) for i in range(3)
        ]
        
        # Configure successful processing
        self.gmail_service.get_unread_emails.return_value = test_emails
        analysis = EmailAnalysis(
            category=EmailCategory.NON_ESSENTIAL,
            confidence=0.95,
            reasoning="Test content",
            summary=None
        )
        self.email_analyzer.analyze_email.return_value = analysis
        
        # Configure successful database operations
        self.db_manager.store_deleted_email.return_value = True
        
        # Process emails
        self.email_manager.process_unread_emails(batch_size=3)
        
        # Verify all emails were processed
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 3)
        
        # Verify proper cleanup
        self.assertEqual(self.gmail_service.move_to_trash.call_count, 3)
        self.assertEqual(self.db_manager.store_deleted_email.call_count, 3)
        self.assertEqual(self.db_manager.add_processing_history.call_count, 3)
        
        # Verify each email was properly handled
        for email in test_emails:
            # Verify email was moved to trash
            self.gmail_service.move_to_trash.assert_any_call(email.email_id)
            
            # Verify email was stored in database
            self.db_manager.store_deleted_email.assert_any_call(
                email_id=email.email_id,
                subject=email.subject,
                sender=email.sender,
                content=email.content
            )
            
            # Verify processing history was added
            self.db_manager.add_processing_history.assert_any_call(
                email_id=email.email_id,
                action="processed",
                category=analysis.category,
                confidence=analysis.confidence,
                success=True,
                reasoning=analysis.reasoning
            )

if __name__ == '__main__':
    unittest.main()
