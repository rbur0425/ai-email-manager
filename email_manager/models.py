from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from email_manager.database.models import EmailCategory

@dataclass
class EmailContent:
    """Data class for email content"""
    email_id: str
    subject: str
    sender: str
    content: str
    received_date: datetime

@dataclass
class EmailAnalysis:
    """Data class for email analysis results"""
    category: EmailCategory
    confidence: float
    reasoning: str
    error_message: Optional[str] = None
    summary: Optional[str] = None  # Only for tech/AI emails
