import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum as SQLAlchemyEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class EmailCategory(str, Enum):
    """Email categories enum matching the database enum"""
    TECH_AI = 'TECH_AI'
    NON_ESSENTIAL = 'NON_ESSENTIAL'
    IMPORTANT = 'IMPORTANT'

    def __str__(self) -> str:
        """Return the value when converting to string."""
        return self.value

class DeletedEmail(Base):
    """Model for storing metadata of deleted emails"""
    __tablename__ = 'deleted_emails'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(String(255), unique=True, nullable=False)
    subject = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)
    content = Column(Text)  # Optional, for potential recovery
    deletion_date = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<DeletedEmail(email_id='{self.email_id}', subject='{self.subject}')>"

class TechContent(Base):
    """Model for archiving tech/AI related content"""
    __tablename__ = 'tech_content'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(String(255), unique=True, nullable=False)
    subject = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    received_date = Column(DateTime(timezone=True), nullable=False)
    category = Column(SQLAlchemyEnum(EmailCategory), nullable=False)
    archived_date = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<TechContent(email_id='{self.email_id}', subject='{self.subject}')>"

class ProcessingHistory(Base):
    """Model for tracking email processing history"""
    __tablename__ = 'processing_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(String(255), nullable=False)
    processing_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    action = Column(String(50), nullable=False)  # 'deleted', 'archived', 'marked_read'
    category = Column(SQLAlchemyEnum(EmailCategory), nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)

    def __repr__(self):
        return f"<ProcessingHistory(email_id='{self.email_id}', action='{self.action}', success={self.success})>"
