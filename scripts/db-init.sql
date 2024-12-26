-- Initialize Email Manager Database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum for email categories
CREATE TYPE email_category AS ENUM ('tech_ai', 'non_essential', 'important');

-- Deleted Emails Table
CREATE TABLE deleted_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    content TEXT,  -- Store content for potential recovery
    deletion_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tech/AI Content Archive
CREATE TABLE tech_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    received_date TIMESTAMP WITH TIME ZONE NOT NULL,
    category email_category NOT NULL,
    archived_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Processing History Table (for tracking and analysis)
CREATE TABLE processing_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id VARCHAR(255) NOT NULL,
    processing_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(50) NOT NULL,  -- 'deleted', 'archived', 'marked_read'
    category email_category NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- Create indexes
CREATE INDEX idx_deleted_emails_email_id ON deleted_emails(email_id);
CREATE INDEX idx_tech_content_email_id ON tech_content(email_id);
CREATE INDEX idx_processing_history_email_id ON processing_history(email_id);
CREATE INDEX idx_tech_content_category ON tech_content(category);
CREATE INDEX idx_deleted_emails_deletion_date ON deleted_emails(deletion_date);
CREATE INDEX idx_tech_content_received_date ON tech_content(received_date);

-- Add comments
COMMENT ON TABLE deleted_emails IS 'Stores metadata for emails that have been moved to trash';
COMMENT ON TABLE tech_content IS 'Archives important technical and AI-related content with summaries';
COMMENT ON TABLE processing_history IS 'Tracks all email processing operations for analysis and debugging';