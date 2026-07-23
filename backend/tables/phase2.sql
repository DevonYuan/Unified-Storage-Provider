-- OmniDrive Database Schema - Phase 2
-- Google Drive Integration

-- Google OAuth tokens table for storing OAuth 2.0 tokens per user
CREATE TABLE google_oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Google Drive files metadata table for caching file information
CREATE TABLE google_files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    file_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(255) NOT NULL,
    size BIGINT,
    parent_id VARCHAR(255),
    modified_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, file_id)
);

-- Indexes for better query performance
CREATE INDEX idx_google_oauth_tokens_user_id ON google_oauth_tokens(user_id);
CREATE INDEX idx_google_oauth_tokens_expires_at ON google_oauth_tokens(expires_at);
CREATE INDEX idx_google_files_user_id ON google_files(user_id);
CREATE INDEX idx_google_files_parent_id ON google_files(parent_id);
CREATE INDEX idx_google_files_modified_time ON google_files(modified_time);

-- Trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_google_oauth_tokens_updated_at BEFORE UPDATE ON google_oauth_tokens
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_google_files_updated_at BEFORE UPDATE ON google_files
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Notes:
-- This schema extends the authentication system with Google Drive integration.
-- google_oauth_tokens stores OAuth 2.0 tokens for each connected user.
-- google_files caches Google Drive file metadata to reduce API calls.
-- Future phases will add OneDrive integration and unified file metadata tables.
