"""
Email Manager module for processing and categorizing emails using Gmail API and Claude AI.

This module provides the main orchestration logic for the email management system.
It coordinates between Gmail service, Claude AI analyzer, and database operations
to process emails based on their content and importance.
"""

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
    """Custom exception for email processing errors.
    
    This exception is raised when there are issues during email processing,
    such as API failures, database errors, or invalid email content.
    """
    pass

class EmailManager:
    """Main class for managing email processing workflow.
    
    This class orchestrates the interaction between different components:
    - Gmail Service for email operations
    - Email Analyzer for content analysis
    - Database Manager for storing results
    
    Attributes:
        gmail (GmailService): Service for Gmail operations
        analyzer (EmailAnalyzer): Service for analyzing email content
        db (DatabaseManager): Service for database operations
    """
    
    def __init__(self, gmail_service: GmailService, email_analyzer: EmailAnalyzer, db_manager: DatabaseManager):
        """Initialize EmailManager with required services.
        
        Args:
            gmail_service: Instance of GmailService for email operations
            email_analyzer: Instance of EmailAnalyzer for content analysis
            db_manager: Instance of DatabaseManager for database operations
        """
        self.gmail = gmail_service
        self.analyzer = email_analyzer
        self.db = db_manager
        
    def process_unread_emails(self, batch_size: int = 10, max_retries: int = 3) -> None:
        """Process a batch of unread emails.
        
        Fetches and processes unread emails in batches. Each email is analyzed
        and handled according to its category (non-essential, tech/AI, important).
        
        Args:
            batch_size: Number of emails to process in one batch
            max_retries: Maximum number of retry attempts for failed operations
            
        Raises:
            EmailProcessingError: If batch processing fails
        """
        try:
            emails = self.gmail.get_unread_emails(max_results=batch_size)
            logger.info(f"Found {len(emails)} unread emails to process")
            
            for email in emails:
                self._process_single_email(email, max_retries)
                
        except Exception as e:
            logger.error(f"Error processing batch of emails: {e}")
            raise EmailProcessingError(f"Batch processing failed: {str(e)}")
    
    def _process_single_email(self, email: EmailContent, max_retries: int) -> None:
        """Process a single email with retries.
        
        Analyzes the email content and processes it based on the analysis results.
        Implements retry logic for handling transient failures.
        
        Args:
            email: Email content to process
            max_retries: Maximum number of retry attempts
            
        Raises:
            EmailProcessingError: If processing fails after all retries
        """
        retries = 0
        error_msg = None
        while retries < max_retries:
            try:
                logger.debug(f"Processing attempt {retries + 1} for email {email.email_id}")
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
                self.db.add_processing_history(
                    email_id=email.email_id,
                    action="processed",
                    category=analysis.category,
                    confidence=analysis.confidence,
                    success=True,
                    reasoning=analysis.reasoning
                )
                logger.debug(f"Successfully processed email {email.email_id} on attempt {retries + 1}")
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                retries += 1
                logger.warning(f"Attempt {retries} failed for email {email.email_id}: {error_msg}")
                if retries == max_retries:
                    logger.error(f"All {max_retries} attempts failed for email {email.email_id}")
                    self._handle_processing_failure(email, error_msg)
                    raise EmailProcessingError(f"Failed to process email after {max_retries} attempts: {error_msg}")
                else:
                    time.sleep(2 ** retries)  # Exponential backoff
    
    def _handle_non_essential_email(self, email: EmailContent) -> None:
        """Handle non-essential email processing.
        
        Stores the email metadata in the database and moves it to trash.
        
        Args:
            email: Email to process
            
        Raises:
            EmailProcessingError: If storage or trash operation fails
        """
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
        """Handle tech/AI related email processing.
        
        Archives the email content with its summary and moves original to trash.
        
        Args:
            email: Email to process
            analysis: Analysis results
            
        Raises:
            EmailProcessingError: If archiving or trash operation fails
        """
        logger.info(f"Processing tech email: {email.email_id}")
        
        # Generate summary for tech content
        try:
            summary = self.analyzer.generate_summary(email)
            logger.debug(f"Generated summary for tech email: {summary}")
            if summary is None:
                raise EmailProcessingError("Failed to generate summary for tech email")
        except (ClaudeAPIError, InsufficientCreditsError) as e:
            raise EmailProcessingError(f"Failed to generate summary: {str(e)}")
        
        # Store in tech content archive
        logger.debug(f"Attempting to store tech content for email {email.email_id}")
        stored = self.db.archive_tech_content(
            email_id=email.email_id,
            subject=email.subject,
            sender=email.sender,
            content=email.content,
            summary=summary,
            received_date=email.received_date,
            category=EmailCategory.TECH_AI
        )
        logger.debug(f"Store tech content result for {email.email_id}: {stored}")
        
        if stored:
            # Move to trash only after successful archiving
            self.gmail.move_to_trash(email.email_id)
            logger.info(f"Tech email {email.email_id} archived and moved to trash")
        else:
            error_msg = f"Failed to archive tech email {email.email_id}"
            logger.error(error_msg)
            raise EmailProcessingError(error_msg)

    def _handle_important_email(self, email: EmailContent) -> None:
        """Handle important email processing.
        
        Marks the email as read but keeps it in the inbox.
        
        Args:
            email: Email to process
        """
        logger.info(f"Processing important email: {email.email_id}")
        
        # Mark as read but don't delete
        self.gmail.mark_as_read(email.email_id)
        logger.info(f"Important email {email.email_id} marked as read")
    
    def _handle_processing_failure(self, email: EmailContent, error_message: str) -> None:
        """Handle email processing failure.
        
        Logs the failure and marks the email as unread for future processing.
        
        Args:
            email: Failed email
            error_message: Description of the failure
        """
        logger.error(f"Failed to process email {email.email_id} after all retries: {error_message}")
        
        # Log the failure
        self.db.add_processing_history(
            email_id=email.email_id,
            action="failed",
            category=EmailCategory.IMPORTANT,  # Default to important on failure
            confidence=0.0,  # Zero confidence for failures
            success=False,
            error_message=error_message,
            reasoning="Failed to process email"
        )
        
        # Mark as unread so it can be processed in next batch
        try:
            self.gmail.mark_as_unread(email.email_id)
        except Exception as e:
            logger.error(f"Failed to mark failed email as unread: {e}")
