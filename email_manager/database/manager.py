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
    def __init__(self):
        """Initialize database connection and session factory"""
        connection_string = f"postgresql://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{config.db.name}"
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)

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
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def store_deleted_email(self, email_id: str, subject: str, sender: str, content: Optional[str] = None) -> bool:
        """Store metadata for a deleted email"""
        try:
            with self.get_session() as session:
                deleted_email = DeletedEmail(
                    email_id=email_id,
                    subject=subject,
                    sender=sender,
                    content=content
                )
                session.add(deleted_email)
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error storing deleted email: {e}")
            return False

    def store_tech_content(
        self, 
        email_id: str, 
        subject: str, 
        sender: str, 
        content: str,
        summary: str,
        received_date: str,
        category: EmailCategory
    ) -> bool:
        """Archive tech/AI related content"""
        try:
            with self.get_session() as session:
                tech_content = TechContent(
                    email_id=email_id,
                    subject=subject,
                    sender=sender,
                    content=content,
                    summary=summary,
                    received_date=received_date,
                    category=category
                )
                session.add(tech_content)
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error storing tech content: {e}")
            return False

    def log_processing(
        self,
        email_id: str,
        action: str,
        category: EmailCategory,
        success: bool,
        error_message: Optional[str] = None
    ) -> bool:
        """Log email processing history"""
        try:
            logger.debug(f"Logging processing with category: {category}, type: {type(category)}, value: {category.value}")
            with self.get_session() as session:
                history = ProcessingHistory(
                    email_id=email_id,
                    action=action,
                    category=category,
                    success=success,
                    error_message=error_message
                )
                session.add(history)
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error logging processing history: {e}")
            return False

    def get_tech_content(self, limit: int = 100) -> List[TechContent]:
        """Retrieve recent tech content entries"""
        try:
            with self.get_session() as session:
                return session.query(TechContent)\
                    .order_by(TechContent.received_date.desc())\
                    .limit(limit)\
                    .all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving tech content: {e}")
            return []

    def get_processing_history(self, email_id: str) -> List[ProcessingHistory]:
        """Get processing history for a specific email"""
        try:
            with self.get_session() as session:
                return session.query(ProcessingHistory)\
                    .filter(ProcessingHistory.email_id == email_id)\
                    .order_by(ProcessingHistory.processing_date.desc())\
                    .all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving processing history: {e}")
            return []

    def clear_tables(self) -> None:
        """Clear all tables in the database. Use only for testing."""
        try:
            with self.get_session() as session:
                session.query(DeletedEmail).delete()
                session.query(TechContent).delete()
                session.query(ProcessingHistory).delete()
                session.commit()
                logger.info("All tables cleared successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error clearing tables: {e}")
            raise
