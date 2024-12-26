"""
Initialize the PostgreSQL database for the Email Manager.
"""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_database():
    """Initialize the database with required tables and indexes."""
    # Get database connection parameters from environment
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    # Read SQL initialization script
    script_path = Path(__file__).parent / 'db-init.sql'
    with open(script_path, 'r') as f:
        sql_script = f.read()
    
    # Connect and initialize database
    try:
        with psycopg2.connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Execute initialization script
                cur.execute(sql_script)
                print("Database initialized successfully!")
    
    except psycopg2.Error as e:
        print(f"Error initializing database: {e}")
        raise

if __name__ == '__main__':
    init_database()