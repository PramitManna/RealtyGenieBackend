-- Migration: Add festive email settings table
-- This table stores user preferences for automated festive email sending

CREATE TABLE IF NOT EXISTS festive_email_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    festive_id VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, festive_id)
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_festive_settings_user_id ON festive_email_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_festive_settings_enabled ON festive_email_settings(enabled) WHERE enabled = TRUE;

-- Add RLS policies
ALTER TABLE festive_email_settings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own settings
CREATE POLICY "Users can read own festive settings"
    ON festive_email_settings
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own settings
CREATE POLICY "Users can insert own festive settings"
    ON festive_email_settings
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own settings
CREATE POLICY "Users can update own festive settings"
    ON festive_email_settings
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy: Users can delete their own settings
CREATE POLICY "Users can delete own festive settings"
    ON festive_email_settings
    FOR DELETE
    USING (auth.uid() = user_id);
