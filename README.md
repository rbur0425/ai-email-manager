```
 █████╗ ██╗    ███████╗███╗   ███╗ █████╗ ██╗██╗     
██╔══██╗██║    ██╔════╝████╗ ████║██╔══██╗██║██║     
███████║██║    █████╗  ██╔████╔██║███████║██║██║     
██╔══██║██║    ██╔══╝  ██║╚██╔╝██║██╔══██║██║██║     
██║  ██║██║    ███████╗██║ ╚═╝ ██║██║  ██║██║███████╗
╚═╝  ╚═╝╚═╝    ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝
███╗   ███╗ █████╗ ███╗   ██╗ █████╗  ██████╗ ███████╗██████╗ 
████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔════╝ ██╔════╝██╔══██╗
██╔████╔██║███████║██╔██╗ ██║███████║██║  ███╗█████╗  ██████╔╝
██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║██║   ██║██╔══╝  ██╔══██╗
██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║╚██████╔╝███████╗██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
```

# AI Email Manager

An intelligent email management system powered by AI to automatically categorize, process, and organize your emails. Built with Python, it leverages Gmail API and Anthropic's Claude AI to make your inbox smarter.

## 🌟 Features

- **Smart Email Categorization**: Automatically categorizes emails into:
  - Important (kept in inbox)
  - Save & Summarize (emails you want to archive with summaries)
  - Non-essential (stored and cleaned up)

- **AI-Powered Analysis**: Uses Claude AI to understand email content and context
- **Gmail Integration**: Seamless integration with Gmail for email operations
- **Robust Error Handling**: Retries with exponential backoff for transient failures
- **Comprehensive Logging**: Detailed logging for monitoring and debugging
- **Database Storage**: Stores processed emails and their metadata for future reference

## 🏗️ System Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│   Gmail API     │     │ Email Manager │     │   Claude AI   │
│  Integration    │◄────┤              ├────►│   Analysis    │
└─────────────────┘     │  Orchestrator│     └───────────────┘
                        │              │     
┌─────────────────┐     │              │     ┌───────────────┐
│    Database     │◄────┤              │     │    Logging    │
│    Storage      │     └──────────────┘     │    System     │
└─────────────────┘                          └───────────────┘
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Gmail Account
- Anthropic API Key
- PostgreSQL Database

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-email-manager.git
   cd ai-email-manager
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - GMAIL_CREDENTIALS_FILE
   # - DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
   # - ANTHROPIC_API_KEY
   ```

5. Initialize the database:
   ```bash
   psql -U your_username -d your_database -f scripts/db-init.sql
   ```

### Running Tests

Run all tests:
```bash
python -m unittest discover -v
```

Run specific test files:
```bash
# End-to-end tests
python -m unittest email_manager.tests.test_end_to_end -v

# Gmail service tests
python -m unittest email_manager.tests.test_gmail_service -v

# Database tests
python -m unittest email_manager.tests.test_database -v

# Analyzer tests
python -m unittest email_manager.tests.test_analyzer -v
```

Run tests with debug logging:
```bash
LOGLEVEL=DEBUG python -m unittest discover -v
```

### Usage

1. Start the email manager with default settings (10 emails):
   ```bash
   python -m email_manager
   ```

2. Process a specific number of emails:
   ```bash
   # Process 100 emails
   python -m email_manager --batch-size 100
   
   # Process 100 emails with 5 retry attempts
   python -m email_manager --batch-size 100 --max-retries 5
   ```

3. Monitor the logs (logs are timestamped):
   ```bash
   # View latest log file
   tail -f logs/email_manager_$(date +%Y%m%d_*)*.log
   
   # View all logs
   tail -f logs/email_manager_*.log
   
   # Search logs for errors
   grep "ERROR" logs/email_manager_*.log
   ```

4. View all available options:
   ```bash
   python -m email_manager --help
   ```

### Common Use Cases

1. **Daily Processing (Small Batch)**
   ```bash
   # Process 20 emails, good for frequent runs
   python -m email_manager --batch-size 20
   ```

2. **Bulk Processing (Large Batch)**
   ```bash
   # Process 100+ emails, good for catching up
   python -m email_manager --batch-size 100
   ```

3. **Careful Processing (More Retries)**
   ```bash
   # Process emails with extra retry attempts
   python -m email_manager --batch-size 50 --max-retries 5
   ```

## 📝 Configuration

The system can be configured through environment variables:

- `GMAIL_CREDENTIALS_FILE`: Path to Gmail API credentials JSON
- `DB_HOST`: Database host
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `BATCH_SIZE`: Number of emails to process in one batch (default: 10)
- `MAX_RETRIES`: Maximum retry attempts for failed operations (default: 3)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Anthropic Claude API](https://anthropic.com)
- [Rich Logger](https://rich.readthedocs.io/)
