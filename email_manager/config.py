"""
Configuration management for the Email Manager application.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class GmailConfig:
    """Gmail-related configuration settings."""
    credentials_file: str
    token_file: Optional[str]
    user_email: str
    scopes: list[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = [
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.labels'
            ]

@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int
    name: str
    user: str
    password: str
    
    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

@dataclass
class ClaudeConfig:
    """Claude AI configuration."""
    api_key: str
    model: str

@dataclass
class Config:
    """Main application configuration."""
    # Application paths
    base_dir: Path
    logs_dir: Path
    
    # Component configurations
    gmail: GmailConfig
    db: DatabaseConfig
    claude: ClaudeConfig
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables."""
        base_dir = Path(__file__).parent.parent
        
        return cls(
            base_dir=base_dir,
            logs_dir=base_dir / 'logs',
            
            gmail=GmailConfig(
                credentials_file=os.getenv('GMAIL_CREDENTIALS_FILE'),
                token_file=os.getenv('GMAIL_TOKEN_FILE'),
                user_email=os.getenv('GMAIL_USER_EMAIL')
            ),
            
            db=DatabaseConfig(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                name=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            ),
            
            claude=ClaudeConfig(
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                model=os.getenv('CLAUDE_MODEL')
            )
        )

    @property
    def ANTHROPIC_API_KEY(self) -> str:
        """Getter for Claude API key to maintain compatibility."""
        return self.claude.api_key

    @property
    def CLAUDE_MODEL(self) -> str:
        """Getter for Claude model name to maintain compatibility."""
        return self.claude.model

# Global configuration instance
config = Config.load()