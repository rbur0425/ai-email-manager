from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..config import config
from ..logger import get_logger
from .models import Base, DeletedEmail, TechContent, ProcessingHistory, EmailCategory

logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self, schema: str = 'public'):
        """Initialize database connection and session factory
        
        Args:
            schema: Database schema to use (defaults to 'public')
        """
        connection_string = f"postgresql://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{config.db.name}"
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.schema = schema

        # Set the schema for SQLAlchemy models
        Base.metadata.schema = schema

    def create_tables(self) -> None:
        """Create database tables if they don't exist"""
        try:
            # Read and execute initialization script
            script_path = Path(__file__).parent.parent.parent / 'scripts' / 'db-init.sql'
            with open(script_path, 'r') as f:
                sql_script = f.read()
            
            with self.engine.connect() as conn:
                conn.execute(text(sql_script))
                conn.commit()
            
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            raise
        except FileNotFoundError as e:
            logger.error(f"Could not find initialization script: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            # Set the search path to include both schema and public (for uuid-ossp)
            session.execute(text(f"SET search_path TO {self.schema}, public"))
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def store_deleted_email(self, email_id: str, subject: str, sender: str, content: Optional[str] = None) -> UUID:
        """Store metadata for a deleted email
        
        Args:
            email_id: Unique identifier of the email
            subject: Email subject
            sender: Email sender
            content: Optional email content for potential recovery
            
        Returns:
            UUID of the created record
            
        Raises:
            SQLAlchemyError: If there's a database error
        """
        record_id = uuid4()
        deleted_email = DeletedEmail(
            id=record_id,
            email_id=email_id,
            subject=subject,
            sender=sender,
            content=content
        )
        
        with self.get_session() as session:
            session.add(deleted_email)
            session.flush()  # Ensure the record is created and id is available
            return record_id

    def archive_tech_content(self, email_id: str, subject: str, sender: str, 
                           content: str, summary: str, received_date: datetime,
                           category: EmailCategory = EmailCategory.TECH_AI) -> UUID:
        """Archive tech/AI related email content
        
        Args:
            email_id: Unique identifier of the email
            subject: Email subject
            sender: Email sender
            content: Full email content
            summary: Generated summary of the content
            received_date: When the email was received (should be timezone-aware)
            category: Email category (defaults to TECH_AI)
            
        Returns:
            UUID of the created record
            
        Raises:
            SQLAlchemyError: If there's a database error
            ValueError: If received_date is not timezone-aware
        """
        if received_date.tzinfo is None:
            raise ValueError("received_date must be timezone-aware")
            
        record_id = uuid4()
        tech_content = TechContent(
            id=record_id,
            email_id=email_id,
            subject=subject,
            sender=sender,
            content=content,
            summary=summary,
            received_date=received_date,
            category=category
        )
        
        with self.get_session() as session:
            session.add(tech_content)
            session.flush()  # Ensure the record is created and id is available
            return record_id

    def record_processing(self, email_id: str, action: str, category: EmailCategory, 
                         success: bool, error_message: Optional[str] = None) -> UUID:
        """Record an email processing action in the history
        
        Args:
            email_id: Unique identifier of the email
            action: Action taken ('deleted', 'archived', 'marked_read')
            category: Email category
            success: Whether the action was successful
            error_message: Optional error message if action failed
            
        Returns:
            UUID of the created record
            
        Raises:
            SQLAlchemyError: If there's a database error
        """
        record_id = uuid4()
        history_record = ProcessingHistory(
            id=record_id,
            email_id=email_id,
            action=action,
            category=category,
            success=success,
            error_message=error_message
        )
        
        with self.get_session() as session:
            session.add(history_record)
            session.flush()  # Ensure the record is created and id is available
            return record_id

    def get_tech_content(self, email_id: str) -> Optional[TechContent]:
        """Retrieve archived tech content by email ID
        
        Args:
            email_id: Unique identifier of the email
            
        Returns:
            TechContent if found, None otherwise
            
        Raises:
            SQLAlchemyError: If there's a database error
        """
        with self.get_session() as session:
            # Query for the content and ensure we get a fresh instance
            result = session.query(TechContent)\
                .filter(TechContent.email_id == email_id)\
                .first()
            
            if result is None:
                return None
            
            # Detach the instance from the session but ensure all attributes are loaded
            session.refresh(result)
            return result

    def get_deleted_email(self, email_id: str) -> Optional[DeletedEmail]:
        """Retrieve deleted email metadata by email ID
        
        Args:
            email_id: Unique identifier of the email
            
        Returns:
            DeletedEmail if found, None otherwise
            
        Raises:
            SQLAlchemyError: If there's a database error
        """
        with self.get_session() as session:
            # Query for the email and ensure we get a fresh instance
            result = session.query(DeletedEmail)\
                .filter(DeletedEmail.email_id == email_id)\
                .first()
            
            if result is None:
                return None
            
            # Detach the instance from the session but ensure all attributes are loaded
            session.refresh(result)
            return result

    def get_processing_history(self, email_id: str) -> List[ProcessingHistory]:
        """Get processing history for an email
        
        Args:
            email_id: Unique identifier of the email
            
        Returns:
            List of ProcessingHistory records for the email, ordered by processing date
            
        Raises:
            SQLAlchemyError: If there's a database error
        """
        with self.get_session() as session:
            # Query for all history records for this email
            history = session.query(ProcessingHistory)\
                .filter(ProcessingHistory.email_id == email_id)\
                .order_by(ProcessingHistory.processing_date)\
                .all()
            
            # Ensure all attributes are loaded before detaching
            for record in history:
                session.refresh(record)
                # Expunge the record so it's fully detached with loaded attributes
                session.expunge(record)
            
            return history

    def clear_tables(self) -> None:
        """Clear all tables in the database. Use only for testing.
        
        This method truncates all tables in the current schema while maintaining
        the table structure. It should only be used for testing purposes.
        
        Raises:
            SQLAlchemyError: If there's a database error
        """
        with self.get_session() as session:
            # Clear all tables in a specific order to handle foreign keys
            session.execute(text(f"TRUNCATE TABLE {self.schema}.processing_history CASCADE"))
            session.execute(text(f"TRUNCATE TABLE {self.schema}.tech_content CASCADE"))
            session.execute(text(f"TRUNCATE TABLE {self.schema}.deleted_emails CASCADE"))
            session.commit()
