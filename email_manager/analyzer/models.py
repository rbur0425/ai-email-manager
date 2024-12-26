from dataclasses import dataclass
from typing import Optional

class ClaudeAPIError(Exception):
    """Base exception for Claude API errors."""
    pass

class InsufficientCreditsError(ClaudeAPIError):
    """Raised when Claude API credits are depleted."""
    pass