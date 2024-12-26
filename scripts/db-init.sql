-- Initialize Email Manager Database

-- Drop existing tables and types
DROP TABLE IF EXISTS processing_history CASCADE;
DROP TABLE IF EXISTS tech_content CASCADE;
DROP TABLE IF EXISTS deleted_emails CASCADE;
DROP TYPE IF EXISTS emailcategory CASCADE;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create email category enum if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'emailcategory') THEN
        CREATE TYPE emailcategory AS ENUM ('TECH_AI', 'NON_ESSENTIAL', 'IMPORTANT');
    END IF;
END $$;

-- Deleted Emails Table
CREATE TABLE IF NOT EXISTS deleted_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    content TEXT,  -- Store content for potential recovery
    deletion_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tech/AI Content Archive
CREATE TABLE IF NOT EXISTS tech_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    received_date TIMESTAMP WITH TIME ZONE NOT NULL,
    category emailcategory NOT NULL,
    archived_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Processing History Table (for tracking and analysis)
CREATE TABLE IF NOT EXISTS processing_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id VARCHAR(255) NOT NULL,
    processing_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(50) NOT NULL,  -- 'deleted', 'archived', 'marked_read'
    category emailcategory NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,  -- Confidence score from analysis
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_deleted_emails_email_id ON deleted_emails(email_id);
CREATE INDEX IF NOT EXISTS idx_tech_content_email_id ON tech_content(email_id);
CREATE INDEX IF NOT EXISTS idx_processing_history_email_id ON processing_history(email_id);
CREATE INDEX IF NOT EXISTS idx_tech_content_category ON tech_content(category);
CREATE INDEX IF NOT EXISTS idx_deleted_emails_deletion_date ON deleted_emails(deletion_date);
CREATE INDEX IF NOT EXISTS idx_tech_content_received_date ON tech_content(received_date);
CREATE INDEX IF NOT EXISTS idx_processing_history_date ON processing_history(processing_date);

-- Add helpful table descriptions
COMMENT ON TABLE deleted_emails IS 'Stores metadata for emails that have been moved to trash';
COMMENT ON TABLE tech_content IS 'Archives important technical and AI-related content with summaries';
COMMENT ON TABLE processing_history IS 'Tracks all email processing operations for analysis and debugging';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO current_user;