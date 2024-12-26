#!/usr/bin/env python3
"""Initialize database tables for email manager."""

import logging
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to Python path to import email_manager
sys.path.append(str(Path(__file__).parent.parent))
from email_manager.config import config
from email_manager.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database tables.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Get connection string from config
        connection_string = config.db.connection_string
        logger.info(f"Connecting to database at {config.db.host}:{config.db.port}/{config.db.name}")
        
        # Create engine and database manager
        engine = create_engine(connection_string)
        
        # Read SQL script first
        sql_path = Path(__file__).parent / 'db-init.sql'
        if not sql_path.exists():
            logger.error(f"SQL script not found at {sql_path}")
            return False
            
        with open(sql_path, 'r') as f:
            sql_script = f.read()
        
        # Execute SQL script to create tables
        logger.info("Creating database tables...")
        with engine.connect() as conn:
            conn.execute(text(sql_script))
            conn.commit()
            
        # Now initialize DatabaseManager and clear tables
        db_manager = DatabaseManager()
        logger.info("Clearing existing tables...")
        db_manager.clear_tables()
        
        logger.info("Database initialization completed successfully")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)