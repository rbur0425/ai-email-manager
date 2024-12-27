import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..config import config
from ..database.manager import DatabaseManager
from ..database.models import Base, DeletedEmail, EmailCategory, SavedEmail, ProcessingHistory

class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class"""

    @classmethod
    def setUpClass(cls):
        """Set up test database schema"""
        # Generate a unique test schema name
        cls.test_schema = "test_schema"
        
        # Create database manager with the test schema
        cls.db_manager = DatabaseManager(schema=cls.test_schema)
        
        # Create test schema
        with cls.db_manager.engine.connect() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {cls.test_schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {cls.test_schema}"))
            conn.execute(text(f"SET search_path TO {cls.test_schema}, public"))
            conn.commit()
        
        # Create tables using the manager's create_tables method
        cls.db_manager.create_tables()

    @classmethod
    def tearDownClass(cls):
        """Clean up test schema"""
        with cls.db_manager.engine.connect() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {cls.test_schema} CASCADE"))
            conn.commit()
        cls.db_manager.engine.dispose()

    def setUp(self):
        """Set up test case"""
        self.db_manager = DatabaseManager(schema=self.test_schema)

    def test_store_deleted_email(self):
        """Test storing deleted email metadata"""
        email_id = "test123"
        subject = "Test Email"
        sender = "test@example.com"
        content = "Test content"

        # Store deleted email
        self.db_manager.store_deleted_email(email_id, subject, sender, content)

        # Verify storage
        with self.db_manager.get_session() as session:
            deleted_email = session.query(DeletedEmail).filter_by(email_id=email_id).first()
            self.assertIsNotNone(deleted_email)
            self.assertEqual(deleted_email.subject, subject)
            self.assertEqual(deleted_email.sender, sender)
            self.assertEqual(deleted_email.content, content)

    def test_archive_saved_email(self):
        """Test archiving email content that should be saved"""
        email_id = "save123"
        subject = "Important Update"
        sender = "updates@example.com"
        content = "Important project update"
        summary = "Project summary"
        received_date = datetime.now(timezone.utc)
        category = EmailCategory.SAVE_AND_SUMMARIZE

        # Archive email content
        self.db_manager.archive_saved_email(
            email_id, subject, sender, content, summary, received_date, category
        )

        # Verify archive
        with self.db_manager.get_session() as session:
            saved_email = session.query(SavedEmail).filter_by(email_id=email_id).first()
            self.assertIsNotNone(saved_email)
            self.assertEqual(saved_email.subject, subject)
            self.assertEqual(saved_email.sender, sender)
            self.assertEqual(saved_email.content, content)
            self.assertEqual(saved_email.summary, summary)
            self.assertEqual(saved_email.category, category)

    def test_get_saved_email(self):
        """Test retrieving archived email content"""
        # First archive some content
        email_id = "save456"
        subject = "Project News"
        sender = "project@example.com"
        content = "Project updates"
        summary = "Project summary"
        received_date = datetime.now(timezone.utc)
        category = EmailCategory.SAVE_AND_SUMMARIZE

        self.db_manager.archive_saved_email(
            email_id, subject, sender, content, summary, received_date, category
        )

        # Retrieve and verify
        with self.db_manager.get_session() as session:
            saved_email = session.query(SavedEmail).filter_by(email_id=email_id).first()
            self.assertIsNotNone(saved_email)
            self.assertEqual(saved_email.email_id, email_id)
            self.assertEqual(saved_email.subject, subject)
            self.assertEqual(saved_email.content, content)

    def test_record_processing(self):
        """Test recording email processing history"""
        email_id = "test123"
        action = "deleted"
        category = EmailCategory.NON_ESSENTIAL
        success = True
        error_message = None
        confidence = 0.95
        reasoning = "This is a promotional email"

        with self.db_manager.get_session() as session:
            history = self.db_manager.add_processing_history(
                email_id=email_id,
                action=action,
                category=category,
                confidence=confidence,
                success=success,
                error_message=error_message,
                session=session,
                reasoning=reasoning
            )
            session.commit()

            self.assertEqual(history.email_id, email_id)
            self.assertEqual(history.action, action)
            self.assertEqual(history.category, category)
            self.assertEqual(history.confidence, confidence)
            self.assertEqual(history.success, success)
            self.assertEqual(history.error_message, error_message)

    def test_get_processing_history(self):
        """Test retrieving email processing history"""
        email_id = "test123"
        action = "deleted"
        category = EmailCategory.NON_ESSENTIAL
        success = True
        error_message = None

        # Add processing history
        with self.db_manager.get_session() as session:
            self.db_manager.add_processing_history(
                email_id=email_id,
                action=action,
                category=category,
                confidence=0.95,
                success=success,
                error_message=error_message,
                session=session
            )
            session.commit()

        # Get history
        with self.db_manager.get_session() as session:
            history = session.query(ProcessingHistory).filter_by(email_id=email_id).all()
            self.assertIsNotNone(history)
            self.assertEqual(len(history), 1)
            latest_record = history[0]
            self.assertEqual(latest_record.email_id, email_id)
            self.assertEqual(latest_record.action, action)
            self.assertEqual(latest_record.category, category)

    def test_add_processing_history(self):
        """Test adding processing history."""
        email_id = "test123"
        action = "analyzed"
        category = EmailCategory.SAVE_AND_SUMMARIZE
        confidence = 0.95
        success = True

        with self.db_manager.get_session() as session:
            history = self.db_manager.add_processing_history(
                email_id=email_id,
                action=action,
                category=category,
                confidence=confidence,
                success=success,
                session=session
            )
            session.commit()
            
            # Test within the session context
            self.assertEqual(history.email_id, email_id)
            self.assertEqual(history.action, action)
            self.assertEqual(history.category, category)
            self.assertEqual(history.confidence, confidence)
            self.assertEqual(history.success, success)
            self.assertIsNone(history.error_message)

    def test_add_processing_history_with_error(self):
        """Test adding processing history with error."""
        email_id = "test123"
        action = "analyzed"
        category = EmailCategory.SAVE_AND_SUMMARIZE
        confidence = 0.95
        success = False
        error_message = "Test error"

        with self.db_manager.get_session() as session:
            history = self.db_manager.add_processing_history(
                email_id=email_id,
                action=action,
                category=category,
                confidence=confidence,
                success=success,
                error_message=error_message,
                session=session
            )
            session.commit()

            # Test within the session context
            self.assertEqual(history.email_id, email_id)
            self.assertEqual(history.action, action)
            self.assertEqual(history.category, category)
            self.assertEqual(history.confidence, confidence)
            self.assertEqual(history.success, success)
            self.assertEqual(history.error_message, error_message)

    def test_clear_tables(self):
        """Test clearing all tables in the database"""
        # First add some data
        email_id = "test123"
        
        # Add deleted email
        self.db_manager.store_deleted_email(
            email_id, "Test Clear", "clear@example.com", "Clear content"
        )
        
        # Add saved email
        self.db_manager.archive_saved_email(
            email_id,
            "Clear Saved",
            "clear@example.com",
            "Clear saved content",
            "Clear summary",
            datetime.now(timezone.utc),
            EmailCategory.SAVE_AND_SUMMARIZE
        )
        
        # Add processing history
        with self.db_manager.get_session() as session:
            self.db_manager.add_processing_history(
                email_id=email_id,
                action="deleted",
                category=EmailCategory.NON_ESSENTIAL,
                confidence=0.95,
                success=True,
                session=session
            )
            session.commit()
        
        # Clear tables
        self.db_manager.clear_tables()
        
        # Verify all tables are empty
        with self.db_manager.get_session() as session:
            self.assertEqual(session.query(DeletedEmail).count(), 0)
            self.assertEqual(session.query(SavedEmail).count(), 0)
            self.assertEqual(session.query(ProcessingHistory).count(), 0)

if __name__ == '__main__':
    unittest.main()
