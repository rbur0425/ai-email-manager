from dataclasses import dataclass
from enum import Enum
from typing import Optional

class EmailCategory(Enum):
    NON_ESSENTIAL = "non_essential"
    TECH_AI = "tech_ai"
    IMPORTANT = "important"

class ClaudeAPIError(Exception):
    """Base exception for Claude API errors."""
    pass

class InsufficientCreditsError(ClaudeAPIError):
    """Raised when Claude API credits are depleted."""
    pass

@dataclass
class EmailAnalysis:
    category: EmailCategory
    confidence: float
    reasoning: str
    summary: Optional[str] = None  # Only for tech/AI emails

@dataclass
class EmailContent:
    email_id: str
    subject: str
    sender: str
    content: str
    date: str