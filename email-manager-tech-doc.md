# Email Management System with Claude AI
## Technical Documentation

### Overview
This document outlines the technical specifications for an automated email management system that uses Claude AI to analyze Gmail messages and organize them based on content type. The system will automatically identify and remove non-essential emails while preserving and summarizing important tech and AI-related content.

### System Architecture

#### Components
1. Gmail API Integration
   - Handles authentication and email access
   - Manages email operations (read, move to trash)
   - Monitors unread email status

2. Claude AI Integration
   - Processes email content
   - Generates summaries for tech/AI content
   - Makes classification decisions

3. Database Layer
   - Stores deleted email metadata
   - Archives tech/AI content with summaries
   - Tracks system operations

4. Main Application Logic
   - Orchestrates component interactions
   - Implements business rules
   - Handles error cases

### Technical Requirements

#### Dependencies
```python
requirements.txt:
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.0.0
anthropic>=0.3.0
psycopg2-binary>=2.9.0
python-dotenv>=0.19.0
```

#### Environment Variables
```plaintext
GMAIL_CREDENTIALS_FILE=path/to/credentials.json
ANTHROPIC_API_KEY=your_api_key
DB_HOST=localhost
DB_NAME=email_manager
DB_USER=postgres
DB_PASSWORD=your_password
```

### Database Schema

```sql
-- Deleted Emails Table
CREATE TABLE deleted_emails (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    deletion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tech/AI Content Archive
CREATE TABLE tech_content (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    received_date TIMESTAMP NOT NULL,
    category VARCHAR(50) NOT NULL,
    archived_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Implementation Details

#### 1. Gmail Integration Class
```python
class GmailService:
    def __init__(self, credentials_path):
        self.service = self._authenticate(credentials_path)
    
    def _authenticate(self, credentials_path):
        # Gmail OAuth2 authentication implementation
        pass
    
    def get_unread_emails(self):
        # Fetch unread emails from Gmail
        pass
    
    def move_to_trash(self, email_id):
        # Move email to trash
        pass
    
    def mark_as_read(self, email_id):
        # Mark email as read
        pass
```

#### 2. Claude AI Integration Class
```python
class EmailAnalyzer:
    def __init__(self, api_key):
        self.client = anthropic.Client(api_key=api_key)
    
    def analyze_email(self, content):
        # Function calling example for Claude
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"Analyze this email content and determine if it's: "
                          f"1. Advertisement/Non-essential "
                          f"2. Tech/AI related content "
                          f"3. Other important content\n\n{content}"
            }],
            system="You are an email analyzer. Categorize emails and provide summaries for tech/AI content."
        )
        return self._parse_response(response)
    
    def generate_summary(self, content):
        # Generate summary for tech/AI content
        pass
```

#### 3. Database Manager Class
```python
class DatabaseManager:
    def __init__(self, connection_params):
        self.conn = psycopg2.connect(**connection_params)
    
    def record_deleted_email(self, email_id, subject, sender):
        # Record deleted email metadata
        pass
    
    def archive_tech_content(self, email_id, subject, sender, content, summary, category):
        # Archive tech/AI content with summary
        pass
    
    def get_tech_content_archive(self, category=None, date_range=None):
        # Retrieve archived tech content
        pass
```

#### 4. Main Application Class
```python
class EmailManager:
    def __init__(self, gmail_service, email_analyzer, db_manager):
        self.gmail = gmail_service
        self.analyzer = email_analyzer
        self.db = db_manager
    
    def process_unread_emails(self):
        emails = self.gmail.get_unread_emails()
        for email in emails:
            try:
                self._process_single_email(email)
            except Exception as e:
                logging.error(f"Error processing email {email['id']}: {str(e)}")
    
    def _process_single_email(self, email):
        # Main email processing logic
        analysis = self.analyzer.analyze_email(email['content'])
        
        if analysis['category'] == 'non_essential':
            self.gmail.move_to_trash(email['id'])
            self.db.record_deleted_email(email['id'], email['subject'], email['sender'])
        
        elif analysis['category'] == 'tech_ai':
            summary = self.analyzer.generate_summary(email['content'])
            self.db.archive_tech_content(
                email['id'], 
                email['subject'],
                email['sender'],
                email['content'],
                summary,
                analysis['category']
            )
        
        self.gmail.mark_as_read(email['id'])
```

### Usage Example

```python
def main():
    # Initialize components
    gmail_service = GmailService(os.getenv('GMAIL_CREDENTIALS_FILE'))
    email_analyzer = EmailAnalyzer(os.getenv('ANTHROPIC_API_KEY'))
    db_manager = DatabaseManager({
        'host': os.getenv('DB_HOST'),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    })
    
    # Create email manager instance
    manager = EmailManager(gmail_service, email_analyzer, db_manager)
    
    # Process emails
    manager.process_unread_emails()

if __name__ == "__main__":
    main()
```

### Error Handling and Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_manager.log'),
        logging.StreamHandler()
    ]
)
```

### Security Considerations

1. OAuth 2.0 Authentication
   - Use secure token storage
   - Implement token refresh mechanism
   - Handle revoked access appropriately

2. Database Security
   - Use connection pooling
   - Implement prepared statements
   - Encrypt sensitive data

3. API Key Management
   - Use environment variables
   - Implement key rotation
   - Monitor API usage

### Future Enhancements

1. Email Classification Improvements
   - Fine-tune classification criteria
   - Add user feedback mechanism
   - Implement learning from corrections

2. Performance Optimization
   - Batch processing for multiple emails
   - Caching frequently accessed data
   - Async processing for non-blocking operations

3. User Interface
   - Web dashboard for viewing archived content
   - Email classification statistics
   - Manual override capabilities

### Deployment Guidelines

1. Prerequisites
   - Python 3.9+
   - PostgreSQL 12+
   - Gmail API credentials
   - Anthropic API access

2. Installation Steps
   - Clone repository
   - Install dependencies
   - Set up environment variables
   - Initialize database
   - Configure Gmail OAuth2

3. Monitoring
   - Set up error alerts
   - Monitor API usage
   - Track database performance
   - Log processing statistics
