"""
End-to-end test for the Email Manager system.
Testing non-essential, tech, important email processing, error handling, batch processing,
edge cases, and infrastructure failures.
"""
import unittest
from datetime import datetime
import pytz
from unittest.mock import MagicMock, patch

from email_manager.database import EmailCategory
from email_manager.manager import EmailManager, EmailProcessingError
from email_manager.models import EmailContent, EmailAnalysis

class TestEmailManagerE2E(unittest.TestCase):
    """End-to-end test suite for the Email Manager system."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create mock services with all required methods
        self.gmail_service = MagicMock()
        self.email_analyzer = MagicMock()
        self.db_manager = MagicMock()
        
        # Configure db_manager mock with required methods
        self.db_manager.store_deleted_email.return_value = True
        self.db_manager.archive_tech_content.return_value = True
        self.db_manager.record_processing.return_value = True
        
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
        self.db_manager.record_processing.assert_called_once()
    
    def test_tech_email_flow(self):
        """Test complete flow for tech/AI email processing."""
        # Reset mock call counts from previous tests
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Setup mock returns
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        self.email_analyzer.analyze_email.return_value = EmailAnalysis(
            category=EmailCategory.TECH_AI,
            confidence=0.90,
            reasoning="Technical content detected",
            summary="Summary of tech content"
        )
        
        # Execute
        self.email_manager.process_unread_emails(batch_size=1)
        
        # Verify flow
        self.gmail_service.get_unread_emails.assert_called_once()
        self.email_analyzer.analyze_email.assert_called_once_with(self.test_email)
        self.db_manager.archive_tech_content.assert_called_once()
        self.gmail_service.move_to_trash.assert_called_once_with(self.test_email.email_id)
        self.db_manager.record_processing.assert_called_once()

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
        self.db_manager.record_processing.assert_called_once()
        
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
        self.db_manager.record_processing.assert_called_once()
        
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
        
        tech_email = EmailContent(
            email_id="tech456",
            subject="AI Update",
            sender="tech@example.com",
            content="New AI developments",
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
            tech_email,
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
            elif email.email_id == "tech456":
                return EmailAnalysis(
                    category=EmailCategory.TECH_AI,
                    confidence=0.85,
                    reasoning="Tech content detected",
                    summary="Summary of large technical content"
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
        
        # Verify tech email processing
        self.db_manager.archive_tech_content.assert_called_once()
        self.gmail_service.move_to_trash.assert_any_call("tech456")
        
        # Verify important email processing
        self.gmail_service.mark_as_read.assert_called_once_with("imp789")
        
        # Verify logging for all emails
        self.assertEqual(self.db_manager.record_processing.call_count, 3)

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
                    category=EmailCategory.TECH_AI,
                    confidence=0.85,
                    reasoning="Large technical content detected",
                    summary="Summary of large technical content"
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
        self.db_manager.archive_tech_content.assert_called_once()
        self.gmail_service.move_to_trash.assert_any_call("large456")
        
        # Verify special characters email was marked as important
        self.gmail_service.mark_as_read.assert_called_once_with("special789")
        
        # Verify invalid email was moved to trash
        self.gmail_service.move_to_trash.assert_any_call("invalid101")
        
        # Verify all emails were logged
        self.assertEqual(self.db_manager.record_processing.call_count, 4)

    def test_max_retries_exceeded(self):
        """Test behavior when maximum retries are exceeded.
        
        When max retries are exceeded:
        1. The error should be logged
        2. The email should be marked as unread for retry in next batch
        3. The failure should be logged with IMPORTANT category
        4. An EmailProcessingError should be raised
        """
        # Reset mock call counts
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Configure analyzer to always fail
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        error_message = "Persistent error"
        self.email_analyzer.analyze_email.side_effect = Exception(error_message)
        
        # Execute with reduced max_retries for faster testing
        with self.assertLogs('email_manager.manager', level='DEBUG') as log:
            with self.assertRaises(EmailProcessingError) as context:
                self.email_manager.process_unread_emails(batch_size=1, max_retries=2)
            
            # Print all logs for debugging
            print("\nDebug logs:")
            for msg in log.output:
                print(msg)
            
            # Verify the error message
            error_msg = str(context.exception)
            self.assertIn("Failed to process email after 2 attempts", error_msg)
            self.assertIn(error_message, error_msg)
        
        # Verify retry attempts
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 2)
        
        # Verify error logging
        error_logs = [msg for msg in log.output if "ERROR" in msg]
        self.assertTrue(any(error_message in msg for msg in error_logs))
        
        # Verify email was marked for retry
        self.gmail_service.mark_as_unread.assert_called_once_with(self.test_email.email_id)
        
        # Verify failure was logged with IMPORTANT category (default for failures)
        self.db_manager.record_processing.assert_called_once_with(
            email_id=self.test_email.email_id,
            action="failed",
            category=EmailCategory.IMPORTANT,  # Default to important on failure
            success=False,
            error_message=error_message
        )

    def test_database_failures(self):
        """Test handling of database connection failures.
        
        When database operations fail:
        1. The error should be logged
        2. The email should be marked as unread for retry in next batch
        3. An EmailProcessingError should be raised with the appropriate message
        """
        # Reset mock call counts
        self.gmail_service.reset_mock()
        self.email_analyzer.reset_mock()
        self.db_manager.reset_mock()
        
        # Configure test data
        self.gmail_service.get_unread_emails.return_value = [self.test_email]
        self.email_analyzer.analyze_email.return_value = EmailAnalysis(
            category=EmailCategory.TECH_AI,
            confidence=0.90,
            reasoning="Tech content detected",
            summary="Summary of tech content"
        )
        
        # Simulate database failures
        self.db_manager.archive_tech_content.return_value = False  # Simulate store failure
        
        # Execute with database failures and verify error handling
        with self.assertLogs('email_manager.manager', level='DEBUG') as log:
            with self.assertRaises(EmailProcessingError) as context:
                self.email_manager.process_unread_emails(batch_size=1, max_retries=1)
            
            # Print all logs for debugging
            print("\nDebug logs:")
            for msg in log.output:
                print(msg)
            
            # Verify the error message
            error_msg = str(context.exception)
            self.assertIn("Failed to process email after 1 attempts", error_msg)
            self.assertIn("Failed to archive tech email", error_msg)
            
            # Verify error was logged
            error_logs = [msg for msg in log.output if "ERROR" in msg]
            self.assertTrue(any("Failed to archive tech email" in msg for msg in error_logs))
            
            # Verify debug logs show the flow
            debug_logs = [msg for msg in log.output if "DEBUG" in msg]
            self.assertTrue(any("Attempting to store tech content" in msg for msg in debug_logs))
            self.assertTrue(any("Store tech content result" in msg for msg in debug_logs))
            
            # Verify attempted database operations
            self.assertEqual(self.db_manager.archive_tech_content.call_count, 1)
            
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
        self.db_manager.archive_tech_content.assert_not_called()
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
        self.email_analyzer.analyze_email.return_value = EmailAnalysis(
            category=EmailCategory.NON_ESSENTIAL,
            confidence=0.95,
            reasoning="Test content",
            summary=None
        )
        
        # Process emails
        self.email_manager.process_unread_emails(batch_size=3)
        
        # Verify all emails were processed
        self.assertEqual(self.email_analyzer.analyze_email.call_count, 3)
        
        # Verify proper cleanup
        self.assertEqual(self.gmail_service.move_to_trash.call_count, 3)
        self.assertEqual(self.db_manager.store_deleted_email.call_count, 3)
        self.assertEqual(self.db_manager.record_processing.call_count, 3)
        
        # Verify no emails were left unprocessed
        for email in test_emails:
            self.gmail_service.move_to_trash.assert_any_call(email.email_id)
            self.db_manager.record_processing.assert_any_call(
                email_id=email.email_id,
                action="processed",
                category=EmailCategory.NON_ESSENTIAL,
                success=True
            )

if __name__ == '__main__':
    unittest.main()
