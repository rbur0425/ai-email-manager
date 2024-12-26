import os
from datetime import datetime

from email_manager.analyzer import EmailAnalyzer
from email_manager.database import DatabaseManager
from email_manager.gmail import GmailService
from email_manager.manager import EmailManager
from email_manager.models import EmailContent
from email_manager.logger import get_logger

logger = get_logger(__name__)

def main():
    """Test the email manager system"""
    print("Testing Email Management System...")
    
    try:
        # Initialize components
        print("\nInitializing services...")
        gmail_service = GmailService()
        email_analyzer = EmailAnalyzer()
        db_manager = DatabaseManager()
        
        # Recreate database tables for testing
        print("\nRecreating database tables...")
        db_manager.create_tables()
        
        # Create email manager
        email_manager = EmailManager(gmail_service, email_analyzer, db_manager)
        
        # Process a batch of emails
        print("\nProcessing unread emails...")
        email_manager.process_unread_emails(batch_size=3)  # Start with small batch
        
        print("\nEmail processing complete!")
        
    except Exception as e:
        logger.error(f"Error in test script: {e}")
        print(f"\nError: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
