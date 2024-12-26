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
from ..database.models import Base, DeletedEmail, EmailCategory, TechContent, ProcessingHistory

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

    def test_archive_tech_content(self):
        """Test archiving tech/AI email content"""
        email_id = "tech123"
        subject = "AI News"
        sender = "ai@example.com"
        content = "Latest in AI"
        summary = "AI updates"
        received_date = datetime.now(timezone.utc)
        category = EmailCategory.TECH_AI

        # Archive tech content
        self.db_manager.archive_tech_content(
            email_id, subject, sender, content, summary, received_date, category
        )

        # Verify archive
        with self.db_manager.get_session() as session:
            tech_content = session.query(TechContent).filter_by(email_id=email_id).first()
            self.assertIsNotNone(tech_content)
            self.assertEqual(tech_content.subject, subject)
            self.assertEqual(tech_content.sender, sender)
            self.assertEqual(tech_content.content, content)
            self.assertEqual(tech_content.summary, summary)
            self.assertEqual(tech_content.category, category)

    def test_get_tech_content(self):
        """Test retrieving archived tech content"""
        # First archive some content
        email_id = "tech456"
        subject = "Tech News"
        sender = "tech@example.com"
        content = "Tech updates"
        summary = "Tech summary"
        received_date = datetime.now(timezone.utc)
        category = EmailCategory.TECH_AI

        self.db_manager.archive_tech_content(
            email_id, subject, sender, content, summary, received_date, category
        )

        # Retrieve and verify
        with self.db_manager.get_session() as session:
            tech_content = session.query(TechContent).filter_by(email_id=email_id).first()
            self.assertIsNotNone(tech_content)
            self.assertEqual(tech_content.email_id, email_id)
            self.assertEqual(tech_content.subject, subject)
            self.assertEqual(tech_content.content, content)

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
        category = EmailCategory.TECH_AI
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
        category = EmailCategory.TECH_AI
        confidence = 0.0  # Low confidence for error case
        success = False
        error_message = "Analysis failed"

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
        
        # Add tech content
        self.db_manager.archive_tech_content(
            email_id,
            "Clear Tech",
            "clear@example.com",
            "Clear tech content",
            "Clear summary",
            datetime.now(timezone.utc),
            EmailCategory.TECH_AI
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
            self.assertEqual(session.query(TechContent).count(), 0)
            self.assertEqual(session.query(ProcessingHistory).count(), 0)

if __name__ == '__main__':
    unittest.main()
