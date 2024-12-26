"""Main entry point for the Email Manager application."""

import argparse
import sys
from typing import Optional

from email_manager.analyzer import EmailAnalyzer
from email_manager.database import DatabaseManager
from email_manager.gmail.service import GmailService
from email_manager.logger import get_logger
from email_manager.manager import EmailManager

logger = get_logger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='AI Email Manager - Intelligent email processing system'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of emails to process in one batch (default: 10)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retry attempts for failed operations (default: 3)'
    )
    return parser.parse_args()

def main() -> Optional[int]:
    """Main entry point for the application."""
    try:
        args = parse_args()
        
        # Initialize database first to check tables
        db_manager = DatabaseManager()
        if not db_manager.check_tables_exist():
            logger.error("""
Database tables do not exist. Please run database migrations first:

    python -m email_manager migrate

For development setup, you can also use:
    
    python -m email_manager migrate --dev

This will initialize the database with the required schema.
            """)
            return 1
        
        # Initialize other services
        gmail_service = GmailService()
        email_analyzer = EmailAnalyzer()
        
        # Create email manager
        email_manager = EmailManager(
            gmail_service=gmail_service,
            email_analyzer=email_analyzer,
            db_manager=db_manager
        )
        
        # Process emails
        logger.info(f"Starting email processing with batch size: {args.batch_size}")
        email_manager.process_unread_emails(
            batch_size=args.batch_size,
            max_retries=args.max_retries
        )
        logger.info("Email processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error running email manager: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
