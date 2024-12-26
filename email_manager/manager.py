import time
from datetime import datetime
from typing import List, Optional

from email_manager.analyzer import EmailAnalyzer
from email_manager.database import DatabaseManager, EmailCategory
from email_manager.gmail.service import GmailService
from email_manager.logger import get_logger
from email_manager.models import EmailContent, EmailAnalysis

logger = get_logger(__name__)

class EmailProcessingError(Exception):
    """Custom exception for email processing errors"""
    pass

class EmailManager:
    def __init__(self, gmail_service: GmailService, email_analyzer: EmailAnalyzer, db_manager: DatabaseManager):
        """Initialize EmailManager with required services"""
        self.gmail = gmail_service
        self.analyzer = email_analyzer
        self.db = db_manager
        
    def process_unread_emails(self, batch_size: int = 10, max_retries: int = 3) -> None:
        """Process a batch of unread emails"""
        try:
            emails = self.gmail.get_unread_emails(max_results=batch_size)
            logger.info(f"Found {len(emails)} unread emails to process")
            
            for email in emails:
                self._process_single_email(email, max_retries)
                
        except Exception as e:
            logger.error(f"Error processing batch of emails: {e}")
            raise EmailProcessingError(f"Batch processing failed: {str(e)}")
    
    def _process_single_email(self, email: EmailContent, max_retries: int) -> None:
        """Process a single email with retries"""
        retries = 0
        while retries < max_retries:
            try:
                # Analyze email content
                analysis = self.analyzer.analyze_email(email)
                logger.debug(f"Analysis complete for email {email.email_id}: {analysis.category}")
                
                # Process based on category
                if analysis.category == EmailCategory.NON_ESSENTIAL:
                    self._handle_non_essential_email(email)
                elif analysis.category == EmailCategory.TECH_AI:
                    self._handle_tech_email(email, analysis)
                else:  # Important
                    self._handle_important_email(email)
                
                # Log successful processing
                self.db.log_processing(
                    email_id=email.email_id,
                    action="processed",
                    category=analysis.category,
                    success=True
                )
                logger.debug(f"Logged processing with category: {analysis.category}, type: {type(analysis.category)}, value: {analysis.category.value}")
                break  # Success, exit retry loop
                
            except Exception as e:
                retries += 1
                logger.warning(f"Attempt {retries} failed for email {email.email_id}: {e}")
                if retries == max_retries:
                    self._handle_processing_failure(email, str(e))
                else:
                    time.sleep(2 ** retries)  # Exponential backoff
    
    def _handle_non_essential_email(self, email: EmailContent) -> None:
        """Handle non-essential email processing"""
        logger.info(f"Processing non-essential email: {email.email_id}")
        
        # First store in database
        stored = self.db.store_deleted_email(
            email_id=email.email_id,
            subject=email.subject,
            sender=email.sender,
            content=email.content
        )
        
        if stored:
            # Move to trash only after successful database storage
            self.gmail.move_to_trash(email.email_id)
            logger.info(f"Non-essential email {email.email_id} stored and moved to trash")
        else:
            raise EmailProcessingError(f"Failed to store non-essential email {email.email_id}")
    
    def _handle_tech_email(self, email: EmailContent, analysis: EmailAnalysis) -> None:
        """Handle tech/AI related email processing"""
        logger.info(f"Processing tech email: {email.email_id}")
        
        # Store in tech content archive
        stored = self.db.store_tech_content(
            email_id=email.email_id,
            subject=email.subject,
            sender=email.sender,
            content=email.content,
            summary=analysis.summary,
            received_date=email.received_date,
            category=EmailCategory.TECH_AI
        )
        
        if stored:
            # Move to trash only after successful archiving
            self.gmail.move_to_trash(email.email_id)
            logger.info(f"Tech email {email.email_id} archived and moved to trash")
        else:
            raise EmailProcessingError(f"Failed to archive tech email {email.email_id}")
    
    def _handle_important_email(self, email: EmailContent) -> None:
        """Handle important email processing"""
        logger.info(f"Processing important email: {email.email_id}")
        
        # Mark as read but don't delete
        self.gmail.mark_as_read(email.email_id)
        logger.info(f"Important email {email.email_id} marked as read")
    
    def _handle_processing_failure(self, email: EmailContent, error_message: str) -> None:
        """Handle email processing failure"""
        logger.error(f"Failed to process email {email.email_id} after all retries: {error_message}")
        
        # Log the failure
        self.db.log_processing(
            email_id=email.email_id,
            action="failed",
            category=EmailCategory.IMPORTANT,  # Default to important on failure
            success=False,
            error_message=error_message
        )
        
        # Mark as unread so it can be processed in next batch
        try:
            self.gmail.mark_as_unread(email.email_id)
        except Exception as e:
            logger.error(f"Failed to mark failed email as unread: {e}")
