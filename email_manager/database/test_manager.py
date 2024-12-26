import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..config import config
from .manager import DatabaseManager
from .models import Base, DeletedEmail, EmailCategory, TechContent, ProcessingHistory

class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class"""

    @classmethod
    def setUpClass(cls):
        """Set up test database schema"""
        # Generate a unique test schema name
        cls.test_schema = "test_schema"
        
        # Create database manager with the test schema
        cls.db_manager = DatabaseManager(schema=cls.test_schema)
        
        # Create test schema and tables
        with cls.db_manager.engine.connect() as conn:
            # Create schema if it doesn't exist
            conn.execute(text(f"DROP SCHEMA IF EXISTS {cls.test_schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {cls.test_schema}"))
            
            # Enable uuid-ossp extension in public schema if not already enabled
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public'))
            
            # Set search path to include both test schema and public (for uuid-ossp)
            conn.execute(text(f"SET search_path TO {cls.test_schema}, public"))
            
            # Create email category enum type
            conn.execute(text("""
                CREATE TYPE email_category AS ENUM (
                    'NON_ESSENTIAL', 'TECH_AI', 'IMPORTANT'
                )
            """))
            
            conn.commit()
        
        # Create all tables using SQLAlchemy models
        Base.metadata.schema = cls.test_schema
        Base.metadata.create_all(cls.db_manager.engine)

    @classmethod
    def tearDownClass(cls):
        """Clean up test schema"""
        with cls.db_manager.engine.connect() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {cls.test_schema} CASCADE"))
            conn.commit()
        
        # Dispose of the engine
        cls.db_manager.engine.dispose()

    def setUp(self):
        """Set up test case"""
        # Set search path to include both test schema and public
        with self.db_manager.engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {self.test_schema}, public"))
            conn.execute(text("TRUNCATE TABLE deleted_emails, tech_content, processing_history CASCADE"))
            conn.commit()
        
        # Create test data
        self.test_email_id = "test123"
        self.test_subject = "Test Email Subject"
        self.test_sender = "test@example.com"
        self.test_content = "This is a test email content"

    def test_store_deleted_email(self):
        """Test storing deleted email metadata"""
        # Store a deleted email
        record_id = self.db_manager.store_deleted_email(
            email_id=self.test_email_id,
            subject=self.test_subject,
            sender=self.test_sender,
            content=self.test_content
        )

        # Verify the record was created
        self.assertIsInstance(record_id, UUID)

        # Retrieve and verify the stored record in a new session
        with self.db_manager.get_session() as session:
            stored_email = session.query(DeletedEmail)\
                .filter(DeletedEmail.email_id == self.test_email_id)\
                .first()
            
            # Verify the stored data
            self.assertIsNotNone(stored_email)
            self.assertEqual(stored_email.id, record_id)
            self.assertEqual(stored_email.email_id, self.test_email_id)
            self.assertEqual(stored_email.subject, self.test_subject)
            self.assertEqual(stored_email.sender, self.test_sender)
            self.assertEqual(stored_email.content, self.test_content)
            self.assertIsInstance(stored_email.deletion_date, datetime)

    def test_archive_tech_content(self):
        """Test archiving tech/AI email content"""
        # Test data
        test_summary = "This is a summary of the tech email"
        test_received_date = datetime.now(timezone.utc)  # Use UTC timezone
        
        # Archive tech content
        record_id = self.db_manager.archive_tech_content(
            email_id=self.test_email_id,
            subject=self.test_subject,
            sender=self.test_sender,
            content=self.test_content,
            summary=test_summary,
            received_date=test_received_date,
            category=EmailCategory.TECH_AI
        )

        # Verify the record was created
        self.assertIsInstance(record_id, UUID)

        # Retrieve and verify the stored record in a new session
        with self.db_manager.get_session() as session:
            stored_content = session.query(TechContent)\
                .filter(TechContent.email_id == self.test_email_id)\
                .first()
            
            # Verify the stored data
            self.assertIsNotNone(stored_content)
            self.assertEqual(stored_content.id, record_id)
            self.assertEqual(stored_content.email_id, self.test_email_id)
            self.assertEqual(stored_content.subject, self.test_subject)
            self.assertEqual(stored_content.sender, self.test_sender)
            self.assertEqual(stored_content.content, self.test_content)
            self.assertEqual(stored_content.summary, test_summary)
            self.assertEqual(stored_content.category, EmailCategory.TECH_AI)
            
            # Verify timestamps (comparing UTC timestamps)
            self.assertIsInstance(stored_content.received_date, datetime)
            self.assertIsInstance(stored_content.archived_date, datetime)
            self.assertEqual(
                stored_content.received_date.astimezone(timezone.utc).replace(microsecond=0),
                test_received_date.replace(microsecond=0)
            )

    def test_get_tech_content(self):
        """Test retrieving archived tech content"""
        # Test data
        test_summary = "This is a summary of the tech email"
        test_received_date = datetime.now(timezone.utc)
        
        # Archive tech content
        record_id = self.db_manager.archive_tech_content(
            email_id=self.test_email_id,
            subject=self.test_subject,
            sender=self.test_sender,
            content=self.test_content,
            summary=test_summary,
            received_date=test_received_date,
            category=EmailCategory.TECH_AI
        )

        # Test retrieving existing content
        with self.db_manager.get_session() as session:
            stored_content = session.query(TechContent)\
                .filter(TechContent.email_id == self.test_email_id)\
                .first()
            
            # Verify the stored data
            self.assertIsNotNone(stored_content)
            self.assertEqual(stored_content.id, record_id)
            self.assertEqual(stored_content.email_id, self.test_email_id)
            self.assertEqual(stored_content.subject, self.test_subject)
            self.assertEqual(stored_content.sender, self.test_sender)
            self.assertEqual(stored_content.content, self.test_content)
            self.assertEqual(stored_content.summary, test_summary)
            self.assertEqual(stored_content.category, EmailCategory.TECH_AI)
        
        # Test retrieving non-existent content
        non_existent = self.db_manager.get_tech_content("non_existent_id")
        self.assertIsNone(non_existent)

    def test_record_processing(self):
        """Test recording email processing history"""
        # Test successful processing
        success_record_id = self.db_manager.record_processing(
            email_id=self.test_email_id,
            action="archived",
            category=EmailCategory.TECH_AI,
            success=True
        )
        
        # Test failed processing with error message
        error_msg = "Failed to process email"
        failure_record_id = self.db_manager.record_processing(
            email_id=self.test_email_id,
            action="deleted",
            category=EmailCategory.NON_ESSENTIAL,
            success=False,
            error_message=error_msg
        )

        # Verify records were created
        self.assertIsInstance(success_record_id, UUID)
        self.assertIsInstance(failure_record_id, UUID)

        # Retrieve and verify the processing history
        with self.db_manager.get_session() as session:
            history = session.query(ProcessingHistory)\
                .filter(ProcessingHistory.email_id == self.test_email_id)\
                .order_by(ProcessingHistory.processing_date)\
                .all()
            
            # Verify we have both records
            self.assertEqual(len(history), 2)
            
            # Verify successful processing record
            success_record = history[0]
            self.assertEqual(success_record.id, success_record_id)
            self.assertEqual(success_record.email_id, self.test_email_id)
            self.assertEqual(success_record.action, "archived")
            self.assertEqual(success_record.category, EmailCategory.TECH_AI)
            self.assertTrue(success_record.success)
            self.assertIsNone(success_record.error_message)
            self.assertIsInstance(success_record.processing_date, datetime)
            
            # Verify failed processing record
            failure_record = history[1]
            self.assertEqual(failure_record.id, failure_record_id)
            self.assertEqual(failure_record.email_id, self.test_email_id)
            self.assertEqual(failure_record.action, "deleted")
            self.assertEqual(failure_record.category, EmailCategory.NON_ESSENTIAL)
            self.assertFalse(failure_record.success)
            self.assertEqual(failure_record.error_message, error_msg)
            self.assertIsInstance(failure_record.processing_date, datetime)

    def test_get_processing_history(self):
        """Test retrieving email processing history"""
        # Create multiple processing records
        actions = [
            ("archived", EmailCategory.TECH_AI, True, None),
            ("marked_read", EmailCategory.TECH_AI, True, None),
            ("deleted", EmailCategory.TECH_AI, False, "Permission denied")
        ]
        
        record_ids = []
        for action, category, success, error in actions:
            record_id = self.db_manager.record_processing(
                email_id=self.test_email_id,
                action=action,
                category=category,
                success=success,
                error_message=error
            )
            record_ids.append(record_id)

        # Test retrieving history for existing email
        with self.db_manager.get_session() as session:
            history = session.query(ProcessingHistory)\
                .filter(ProcessingHistory.email_id == self.test_email_id)\
                .order_by(ProcessingHistory.processing_date)\
                .all()
            
            # Verify we got all records in correct order
            self.assertEqual(len(history), len(actions))
            for i, record in enumerate(history):
                action, category, success, error = actions[i]
                self.assertEqual(record.id, record_ids[i])
                self.assertEqual(record.email_id, self.test_email_id)
                self.assertEqual(record.action, action)
                self.assertEqual(record.category, category)
                self.assertEqual(record.success, success)
                self.assertEqual(record.error_message, error)
                self.assertIsInstance(record.processing_date, datetime)
                
                # Verify records are ordered by processing_date
                if i > 0:
                    self.assertLess(history[i-1].processing_date, record.processing_date)
        
        # Test retrieving history for non-existent email
        empty_history = self.db_manager.get_processing_history("non_existent_id")
        self.assertEqual(len(empty_history), 0)

    def test_clear_tables(self):
        """Test clearing all tables in the database"""
        # First create some records in all tables
        test_received_date = datetime.now(timezone.utc)
        
        # Create a deleted email record
        deleted_id = self.db_manager.store_deleted_email(
            email_id=self.test_email_id,
            subject=self.test_subject,
            sender=self.test_sender,
            content=self.test_content
        )
        
        # Create a tech content record
        tech_id = self.db_manager.archive_tech_content(
            email_id="tech_" + self.test_email_id,
            subject=self.test_subject,
            sender=self.test_sender,
            content=self.test_content,
            summary="Test summary",
            received_date=test_received_date,
            category=EmailCategory.TECH_AI
        )
        
        # Create processing history records
        history_id = self.db_manager.record_processing(
            email_id=self.test_email_id,
            action="archived",
            category=EmailCategory.TECH_AI,
            success=True
        )
        
        # Verify records were created
        with self.db_manager.get_session() as session:
            self.assertEqual(session.query(DeletedEmail).count(), 1)
            self.assertEqual(session.query(TechContent).count(), 1)
            self.assertEqual(session.query(ProcessingHistory).count(), 1)
        
        # Clear all tables
        self.db_manager.clear_tables()
        
        # Verify all tables are empty
        with self.db_manager.get_session() as session:
            self.assertEqual(session.query(DeletedEmail).count(), 0)
            self.assertEqual(session.query(TechContent).count(), 0)
            self.assertEqual(session.query(ProcessingHistory).count(), 0)
        
        # Verify we can still create new records
        new_deleted_id = self.db_manager.store_deleted_email(
            email_id="new_" + self.test_email_id,
            subject=self.test_subject,
            sender=self.test_sender,
            content=self.test_content
        )
        
        with self.db_manager.get_session() as session:
            self.assertEqual(session.query(DeletedEmail).count(), 1)
            new_record = session.query(DeletedEmail).first()
            self.assertEqual(new_record.id, new_deleted_id)

if __name__ == '__main__':
    unittest.main()
