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
    def __init__(self, schema: str = 'public', database_name: Optional[str] = None):
        """Initialize database connection and session factory
        
        Args:
            schema: Database schema to use (defaults to 'public')
            database_name: Optional database name to override config
        """
        db_name = database_name or config.db.name
        connection_string = f"postgresql://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{db_name}"
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

    def add_processing_history(
        self, 
        email_id: str, 
        action: str, 
        category: EmailCategory,
        confidence: float,
        success: bool = True,
        error_message: Optional[str] = None,
        session: Optional[Session] = None,
        reasoning: Optional[str] = None
    ) -> ProcessingHistory:
        """Add a record to processing history."""
        history = ProcessingHistory(
            email_id=email_id,
            action=action,
            category=category,
            confidence=confidence,
            success=success,
            error_message=error_message,
            reasoning=reasoning
        )
        
        if session is None:
            with self.get_session() as session:
                session.add(history)
                session.commit()
                return session.query(ProcessingHistory).filter_by(id=history.id).first()
        else:
            session.add(history)
            session.flush()  # Flush to get the ID but don't commit yet
            return history

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
            
            # Create a detached copy with all attributes loaded
            session.refresh(result)
            tech_content = TechContent(
                id=result.id,
                email_id=result.email_id,
                subject=result.subject,
                sender=result.sender,
                content=result.content,
                summary=result.summary,
                received_date=result.received_date,
                category=result.category,
                archived_date=result.archived_date
            )
            return tech_content

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

    def check_tables_exist(self) -> bool:
        """Check if all required database tables exist.
        
        Returns:
            bool: True if all tables exist, False otherwise
        """
        required_tables = {'processing_history', 'tech_content', 'deleted_emails'}
        try:
            with self.engine.connect() as conn:
                # Get list of existing tables
                result = conn.execute(text("""
                    SELECT tablename 
                    FROM pg_catalog.pg_tables 
                    WHERE schemaname = :schema
                """), {'schema': self.schema})
                existing_tables = {row[0] for row in result}
                
                # Check if all required tables exist
                return required_tables.issubset(existing_tables)
        except SQLAlchemyError as e:
            logger.error(f"Error checking tables: {e}")
            return False

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
