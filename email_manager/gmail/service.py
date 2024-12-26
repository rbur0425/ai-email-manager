"""
Gmail service implementation for the Email Manager.
Handles email operations and API interactions.
"""
import base64
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from typing import List, Dict, Any

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from ..config import config
from ..logger import get_logger
from ..models import EmailContent
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
    
    def get_unread_emails(self, max_results: int = 10) -> List[EmailContent]:
        """
        Fetch unread emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of EmailContent objects
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
            
            # Process each message
            processed_emails = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = {header['name']: header['value'] 
                         for header in msg['payload']['headers']}
                
                # Extract content
                if 'parts' in msg['payload']:
                    # Multipart message
                    parts = msg['payload']['parts']
                    content = ''
                    for part in parts:
                        if part['mimeType'] == 'text/plain':
                            data = part['body'].get('data', '')
                            if data:
                                content += base64.urlsafe_b64decode(data).decode()
                else:
                    # Single part message
                    data = msg['payload']['body'].get('data', '')
                    content = base64.urlsafe_b64decode(data).decode() if data else ''
                
                # Create timezone-aware datetime
                timestamp = int(msg['internalDate'])/1000
                received_date = datetime.fromtimestamp(timestamp).astimezone(pytz.UTC)
                
                # Create EmailContent object
                email = EmailContent(
                    email_id=msg['id'],
                    subject=headers.get('Subject', '(No Subject)'),
                    sender=headers.get('From', 'Unknown Sender'),
                    content=content,
                    received_date=received_date
                )
                processed_emails.append(email)
                print(f"Processed email: {email.subject}...")
            
            return processed_emails
            
        except HttpError as error:
            logger.error(f'Error fetching emails: {error}')
            raise
    
    def _get_email_data(self, message_id: str) -> EmailContent:
        """
        Get detailed email data for a specific message ID.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            EmailContent object
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {header['name']: header['value'] 
                     for header in message['payload']['headers']}
            
            # Extract content
            if 'parts' in message['payload']:
                # Multipart message
                parts = message['payload']['parts']
                content = ''
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            content += base64.urlsafe_b64decode(data).decode()
            else:
                # Single part message
                data = message['payload']['body'].get('data', '')
                content = base64.urlsafe_b64decode(data).decode() if data else ''
            
            # Create timezone-aware datetime
            timestamp = int(message['internalDate'])/1000
            received_date = datetime.fromtimestamp(timestamp).astimezone(pytz.UTC)
            
            # Create EmailContent object
            email = EmailContent(
                email_id=message_id,
                subject=headers.get('Subject', '(No Subject)'),
                sender=headers.get('From', 'Unknown Sender'),
                content=content,
                received_date=received_date
            )
            return email
            
        except HttpError as error:
            logger.error(f"Error getting email data for {message_id}: {error}")
            raise
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"Error marking email {message_id} as read: {error}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        """Mark an email as unread."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"Error marking email {message_id} as unread: {error}")
            return False

    def move_to_trash(self, message_id: str) -> bool:
        """Move an email to trash."""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"Error moving email {message_id} to trash: {error}")
            return False


def test_gmail_service():
    """Test the Gmail service functionality."""
    service = GmailService()
    emails = service.get_unread_emails(max_results=3)
    
    if emails:
        print(f"\nFound {len(emails)} unread emails:")
        for email in emails:
            print(f"\nSubject: {email.subject}")
            print(f"From: {email.sender}")
            print(f"Content Preview: {email.content[:100]}...")
    else:
        print("No unread emails found")


if __name__ == "__main__":
    test_gmail_service()