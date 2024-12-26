import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from ..gmail.service import GmailService
from ..models import EmailContent

class TestGmailService(unittest.TestCase):
    """Test cases for GmailService class"""

    def setUp(self):
        """Set up test case"""
        # Create a mock Gmail service
        self.mock_service = MagicMock()
        
        # Patch the GmailAuthenticator to return our mock service
        patcher = patch('email_manager.gmail.service.GmailAuthenticator')
        self.mock_auth = patcher.start()
        self.mock_auth.return_value.get_gmail_service.return_value = self.mock_service
        self.addCleanup(patcher.stop)
        
        # Create GmailService instance
        self.gmail_service = GmailService()

    def test_get_unread_emails(self):
        """Test retrieving unread emails"""
        # Mock response data
        mock_messages = {
            'messages': [
                {'id': '123', 'threadId': 'thread123'},
                {'id': '456', 'threadId': 'thread456'}
            ]
        }
        
        mock_email_1 = {
            'id': '123',
            'internalDate': '1703606400000',  # 2023-12-26 10:00:00 EST
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender1@example.com'},
                    {'name': 'Subject', 'value': 'Test Email 1'},
                    {'name': 'Date', 'value': 'Wed, 26 Dec 2023 10:00:00 -0500'}
                ],
                'body': {'data': 'VGVzdCBDb250ZW50IDE='}  # "Test Content 1" in base64
            }
        }
        
        mock_email_2 = {
            'id': '456',
            'internalDate': '1703610000000',  # 2023-12-26 11:00:00 EST
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender2@example.com'},
                    {'name': 'Subject', 'value': 'Test Email 2'},
                    {'name': 'Date', 'value': 'Wed, 26 Dec 2023 11:00:00 -0500'}
                ],
                'body': {'data': 'VGVzdCBDb250ZW50IDI='}  # "Test Content 2" in base64
            }
        }

        # Configure mock responses
        self.mock_service.users().messages().list().execute.return_value = mock_messages
        self.mock_service.users().messages().get().execute.side_effect = [mock_email_1, mock_email_2]

        # Call the method
        emails = self.gmail_service.get_unread_emails(max_results=2)

        # Verify results
        self.assertEqual(len(emails), 2)
        
        # Check first email
        self.assertEqual(emails[0].email_id, '123')
        self.assertEqual(emails[0].subject, 'Test Email 1')
        self.assertEqual(emails[0].sender, 'sender1@example.com')
        self.assertEqual(emails[0].content, 'Test Content 1')
        
        # Check second email
        self.assertEqual(emails[1].email_id, '456')
        self.assertEqual(emails[1].subject, 'Test Email 2')
        self.assertEqual(emails[1].sender, 'sender2@example.com')
        self.assertEqual(emails[1].content, 'Test Content 2')

    def test_mark_as_read(self):
        """Test marking an email as read"""
        email_id = "test123"
        
        # Call the method
        self.gmail_service.mark_as_read(email_id)
        
        # Verify the API was called correctly
        modify_call = self.mock_service.users().messages().modify
        modify_call.assert_called_once_with(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        )
        modify_call().execute.assert_called_once()

    def test_move_to_trash(self):
        """Test moving an email to trash"""
        email_id = "test123"
        
        # Call the method
        self.gmail_service.move_to_trash(email_id)
        
        # Verify the API was called correctly
        trash_call = self.mock_service.users().messages().trash
        trash_call.assert_called_once_with(
            userId='me',
            id=email_id
        )
        trash_call().execute.assert_called_once()

    def test_api_error_handling(self):
        """Test handling of API errors"""
        # Mock an API error
        self.mock_service.users().messages().list().execute.side_effect = \
            HttpError(resp=MagicMock(status=500), content=b'API Error')
        
        # Verify error handling
        with self.assertRaises(HttpError):
            self.gmail_service.get_unread_emails()

if __name__ == '__main__':
    unittest.main()
