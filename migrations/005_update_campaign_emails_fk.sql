-- Migration: Update campaign_emails foreign key to reference batches
-- Date: 2025-12-08
-- Description: Change campaign_emails.campaign_id foreign key from campaigns table to batches table

-- Step 1: Drop any existing foreign key constraints
ALTER TABLE public.campaign_emails 
DROP CONSTRAINT IF EXISTS campaign_emails_campaign_id_fkey;

ALTER TABLE public.campaign_emails 
DROP CONSTRAINT IF EXISTS campaign_emails_batch_id_fkey;

-- Step 2: Delete orphaned campaign_emails records that reference non-existent campaigns/batches
-- This cleans up any emails that reference IDs that no longer exist
DELETE FROM public.campaign_emails 
WHERE campaign_id IS NOT NULL 
AND campaign_id NOT IN (
    SELECT id FROM public.batches WHERE id IS NOT NULL
);

-- Step 3: Rename campaign_id column to batch_id for clarity (only if not already renamed)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'campaign_emails' 
        AND column_name = 'campaign_id'
    ) THEN
        ALTER TABLE public.campaign_emails 
        RENAME COLUMN campaign_id TO batch_id;
    END IF;
END $$;

-- Step 4: Add new foreign key constraint to batches table
ALTER TABLE public.campaign_emails 
ADD CONSTRAINT campaign_emails_batch_id_fkey 
FOREIGN KEY (batch_id) REFERENCES public.batches(id) ON DELETE CASCADE;

-- Step 5: Update indexes
DROP INDEX IF EXISTS idx_campaign_emails_campaign_id;
CREATE INDEX IF NOT EXISTS idx_campaign_emails_batch_id ON public.campaign_emails(batch_id);

-- Step 6: Add comment to clarify the column purpose
COMMENT ON COLUMN public.campaign_emails.batch_id IS 'References the batch (formerly campaign) that this email belongs to';
