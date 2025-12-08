-- Migration: Merge campaigns functionality into batches table
-- Date: 2025-12-07
-- Description: Consolidate campaign and batch tables - batches will directly handle automations

-- Step 1: Add campaign-related columns to batches table
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS subject TEXT;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS body TEXT;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS email_template TEXT;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS description TEXT;

-- Step 2: Add status columns (campaigns had status tracking)
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS total_recipients INTEGER DEFAULT 0;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS emails_sent INTEGER DEFAULT 0;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS open_rate NUMERIC(5,2) DEFAULT 0;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS click_rate NUMERIC(5,2) DEFAULT 0;
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS response_rate NUMERIC(5,2) DEFAULT 0;

-- Step 3: Add persona column if it doesn't exist (some batches might already have it)
ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS persona TEXT;

-- Step 4: Set default values for existing batches
UPDATE public.batches 
SET 
    total_recipients = lead_count,
    emails_sent = 0,
    open_rate = 0,
    click_rate = 0,
    response_rate = 0,
    persona = COALESCE(persona, 'buyer')
WHERE total_recipients IS NULL;

-- Step 5: Add constraints
ALTER TABLE public.batches ADD CONSTRAINT batches_persona_check 
CHECK (persona IN ('buyer', 'seller', 'investor', 'past_client', 'referral', 'cold_prospect'));

-- Step 6: Update batch status to match campaign statuses
-- Existing batches with 'active'/'inactive' will remain
-- New batches can use 'active', 'paused', 'completed', 'draft'
COMMENT ON COLUMN public.batches.status IS 'Batch status: active, paused, completed, draft, or inactive';

-- Step 7: Add updated_at trigger for batches
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE public.batches ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW());

DROP TRIGGER IF EXISTS update_batches_updated_at ON public.batches;
CREATE TRIGGER update_batches_updated_at
    BEFORE UPDATE ON public.batches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Step 8: Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_batches_user_id ON public.batches(user_id);
CREATE INDEX IF NOT EXISTS idx_batches_status ON public.batches(status);
CREATE INDEX IF NOT EXISTS idx_batches_persona ON public.batches(persona);
CREATE INDEX IF NOT EXISTS idx_batches_created_at ON public.batches(created_at DESC);

-- Step 9: Add comments for documentation
COMMENT ON TABLE public.batches IS 'Consolidated batches table - handles both batch management and campaign automation';
COMMENT ON COLUMN public.batches.subject IS 'Email subject line for batch automation';
COMMENT ON COLUMN public.batches.body IS 'Email body content for batch automation';
COMMENT ON COLUMN public.batches.email_template IS 'Template identifier for email generation';
COMMENT ON COLUMN public.batches.description IS 'Batch description and notes';
COMMENT ON COLUMN public.batches.persona IS 'Target persona for automatic tone mapping';
COMMENT ON COLUMN public.batches.objective IS 'Campaign objective (e.g., Schedule showings, Generate leads)';
COMMENT ON COLUMN public.batches.total_recipients IS 'Total number of leads in this batch';
COMMENT ON COLUMN public.batches.emails_sent IS 'Number of emails sent for this batch';
COMMENT ON COLUMN public.batches.open_rate IS 'Email open rate percentage';
COMMENT ON COLUMN public.batches.click_rate IS 'Email click rate percentage';
COMMENT ON COLUMN public.batches.response_rate IS 'Email response rate percentage';

-- Step 10: Verify the migration
-- Run this query to see the updated structure:
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns 
-- WHERE table_name = 'batches' AND table_schema = 'public'
-- ORDER BY ordinal_position;
