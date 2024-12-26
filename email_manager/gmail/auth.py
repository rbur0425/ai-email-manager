"""
Gmail authentication module for handling OAuth2 flow.
"""
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import config
from ..logger import get_logger

logger = get_logger(__name__)

class GmailAuthenticator:
    """Handles Gmail API authentication using OAuth2."""
    
    def __init__(self):
        """Initialize the Gmail authenticator with configuration."""
        print("Initializing Gmail Authenticator...")
        self.credentials_file = Path(config.gmail.credentials_file)
        # Default token file location if not specified
        token_file = config.gmail.token_file or 'token.json'
        self.token_file = Path(token_file)
        self.scopes = config.gmail.scopes
    
    def get_gmail_service(self):
        """
        Authenticate and return Gmail service object.
        
        Returns:
            googleapiclient.discovery.Resource: Authenticated Gmail service
        """
        creds = self._get_credentials()
        print("Creating Gmail service with authenticated credentials...")
        return build('gmail', 'v1', credentials=creds)
    
    def _get_credentials(self) -> Credentials:
        """
        Get valid credentials, refreshing or running auth flow if necessary.
        """
        creds: Optional[Credentials] = None
        
        # Load existing token if it exists
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file), self.scopes
                )
                print("Loaded existing credentials from token file")
            except Exception as e:
                logger.warning(f"Error loading credentials from token file: {e}")
                creds = None
        
        # If no valid credentials available, let's get them
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                print("Starting OAuth flow to get new credentials...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.scopes
                )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            try:
                self.token_file.parent.mkdir(parents=True, exist_ok=True)
                self.token_file.write_text(creds.to_json())
                print(f"Saved credentials to {self.token_file}")
            except Exception as e:
                logger.error(f"Error saving credentials: {e}")
        
        return creds
    
    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        token_dir = self.token_file.parent
        token_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"Saved credentials to {self.token_file}")
            
            # Secure the token file
            self.token_file.chmod(0o600)
        except Exception as e:
            logger.error(f"Error saving token file: {e}")
            print(f"Error saving token file: {e}")
            raise