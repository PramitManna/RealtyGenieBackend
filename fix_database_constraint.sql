-- SQL script to fix the database constraint issue
-- The current constraint prevents same email for same user across different batches
-- We need to change it to allow same email in different batches

-- Step 1: Drop the existing unique constraint on (user_id, email)
ALTER TABLE leads DROP CONSTRAINT IF EXISTS leads_user_id_email_key;

-- Step 2: Create a new unique constraint on (user_id, email, batch_id)
-- This allows same email for same user but in different batches
ALTER TABLE leads ADD CONSTRAINT leads_user_batch_email_unique UNIQUE (user_id, batch_id, email);

-- Optional: Add an index for better query performance
CREATE INDEX IF NOT EXISTS idx_leads_user_batch_email ON leads (user_id, batch_id, email);