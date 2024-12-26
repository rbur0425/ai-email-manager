# Email Manager Deployment Guide

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Gmail API credentials
- Anthropic Claude API key

## Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd ai-email-manager
   ```

2. **Set Up Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure PostgreSQL**
   ```sql
   CREATE DATABASE email_manager;
   CREATE USER email_manager_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE email_manager TO email_manager_user;
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the project root:
   ```plaintext
   # Gmail Configuration
   GMAIL_CREDENTIALS_FILE=path/to/credentials.json
   GMAIL_TOKEN_FILE=path/to/token.json
   GMAIL_USER_EMAIL=your.email@gmail.com

   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=email_manager
   DB_USER=email_manager_user
   DB_PASSWORD=your_password

   # Claude AI Configuration
   ANTHROPIC_API_KEY=your_api_key
   CLAUDE_MODEL=claude-3-sonnet-20240229

   # Logging Configuration
   LOG_LEVEL=INFO
   ```

5. **Initialize Database Tables**
   ```bash
   python -m email_manager.database.manager --init-db
   ```

6. **Test the Installation**
   ```bash
   python -m email_manager.tests.test_end_to_end
   ```

## Running the Application

### Development Mode
```bash
python -m email_manager.manager
```

### Production Mode
We recommend using a process manager like Supervisor:

1. **Install Supervisor**
   ```bash
   sudo apt-get install supervisor  # On Ubuntu/Debian
   ```

2. **Create Supervisor Configuration**
   Create `/etc/supervisor/conf.d/email_manager.conf`:
   ```ini
   [program:email_manager]
   command=/path/to/venv/bin/python -m email_manager.manager
   directory=/path/to/ai-email-manager
   user=your_user
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/email_manager/err.log
   stdout_logfile=/var/log/email_manager/out.log
   environment=
    PYTHONPATH="/path/to/ai-email-manager",
    PATH="/path/to/venv/bin"
   ```

3. **Start the Service**
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start email_manager
   ```

## Monitoring

1. **Check Application Logs**
   ```bash
   tail -f logs/email_manager.log
   ```

2. **Check Database Status**
   ```bash
   psql -U email_manager_user -d email_manager -c "SELECT COUNT(*) FROM tech_content;"
   ```

3. **Monitor Process**
   ```bash
   sudo supervisorctl status email_manager
   ```

## Backup Strategy

1. **Database Backup**
   ```bash
   # Create backup script
   pg_dump -U email_manager_user email_manager > backup_$(date +%Y%m%d).sql
   ```

2. **Configuration Backup**
   ```bash
   # Backup environment variables and credentials
   cp .env .env.backup_$(date +%Y%m%d)
   cp credentials.json credentials.json.backup_$(date +%Y%m%d)
   ```

## Troubleshooting

1. **Database Connection Issues**
   - Check PostgreSQL service status
   - Verify database credentials
   - Ensure database is accessible from application host

2. **Gmail API Issues**
   - Verify credentials file path
   - Check token expiration
   - Ensure required Gmail API scopes are enabled

3. **Claude API Issues**
   - Verify API key
   - Check API rate limits
   - Monitor API response times

## Security Considerations

1. **API Keys and Credentials**
   - Store securely using environment variables
   - Rotate keys periodically
   - Use least privilege access

2. **Database Security**
   - Use strong passwords
   - Enable SSL for database connections
   - Regular security updates

3. **Application Security**
   - Keep dependencies updated
   - Monitor for security advisories
   - Regular security audits

## Maintenance

1. **Regular Updates**
   ```bash
   git pull origin main
   pip install -r requirements.txt --upgrade
   ```

2. **Database Maintenance**
   ```bash
   # Regular vacuum
   psql -U email_manager_user -d email_manager -c "VACUUM ANALYZE;"
   ```

3. **Log Rotation**
   Configure logrotate to manage log files:
   ```bash
   sudo nano /etc/logrotate.d/email_manager
   ```
   ```
   /var/log/email_manager/*.log {
       daily
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 email_manager_user email_manager_user
   }
   ```
