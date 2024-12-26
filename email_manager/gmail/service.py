"""
Gmail service implementation for the Email Manager.
Handles email operations and API interactions.
"""
import base64
from email.mime.text import MIMEText
from typing import List, Dict, Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from ..config import config
from ..logger import get_logger
from .auth import GmailAuthenticator

logger = get_logger(__name__)

class GmailService:
    """Handles Gmail API operations."""
    
    def __init__(self):
        """Initialize the Gmail service with authentication."""
        print("Initializing Gmail Service...")
        self.authenticator = GmailAuthenticator()
        self.service: Resource = self.authenticator.get_gmail_service()
        print("Gmail Service initialized successfully!")
    
    def get_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries containing id, subject, sender, and content
        """
        try:
            print(f"\nFetching up to {max_results} unread emails...")
            
            # Query for unread emails
            query = 'is:unread'
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            print(f"Found {len(messages)} unread messages")
            
            emails = []
            for message in messages:
                email_data = self._get_email_data(message['id'])
                if email_data:
                    emails.append(email_data)
                    print(f"Processed email: {email_data['subject'][:50]}...")
            
            return emails
            
        except HttpError as error:
            logger.error(f"Error fetching emails: {error}")
            print(f"Error fetching emails: {error}")
            return []
    
    def _get_email_data(self, message_id: str) -> Dict[str, Any]:
        """
        Get detailed email data for a specific message ID.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary containing email details
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            subject = next(
                (header['value'] for header in headers if header['name'].lower() == 'subject'),
                'No Subject'
            )
            sender = next(
                (header['value'] for header in headers if header['name'].lower() == 'from'),
                'No Sender'
            )
            
            # Get email content
            content = self._get_email_content(message)
            
            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'content': content,
                'internal_date': message['internalDate']
            }
            
        except HttpError as error:
            logger.error(f"Error getting email data for {message_id}: {error}")
            print(f"Error getting email data: {error}")
            return {}
    
    def _get_email_content(self, message: Dict[str, Any]) -> str:
        """
        Extract email content from message payload.
        
        Args:
            message: Gmail API message resource
            
        Returns:
            String containing email content
        """
        content = ''
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        content += base64.urlsafe_b64decode(data).decode()
        else:
            # Handle messages with no parts
            data = message['payload']['body'].get('data', '')
            if data:
                content += base64.urlsafe_b64decode(data).decode()
        
        return content
    
    def move_to_trash(self, message_id: str) -> bool:
        """
        Move an email to trash.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Boolean indicating success
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            print(f"Moved email {message_id} to trash")
            return True
            
        except HttpError as error:
            logger.error(f"Error moving email {message_id} to trash: {error}")
            print(f"Error moving email to trash: {error}")
            return False
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Boolean indicating success
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"Marked email {message_id} as read")
            return True
            
        except HttpError as error:
            logger.error(f"Error marking email {message_id} as read: {error}")
            print(f"Error marking email as read: {error}")
            return False

# Test function to verify the service is working
def test_gmail_service():
    """Test the Gmail service functionality."""
    print("\nTesting Gmail Service...")
    
    service = GmailService()
    
    # Test getting unread emails
    print("\nTesting email fetching...")
    emails = service.get_unread_emails(max_results=3)
    
    if emails:
        print(f"\nFound {len(emails)} unread emails:")
        for email in emails:
            print(f"\nSubject: {email['subject']}")
            print(f"From: {email['sender']}")
            print(f"Content Preview: {email['content'][:100]}...")
    else:
        print("No unread emails found")

if __name__ == "__main__":
    test_gmail_service()