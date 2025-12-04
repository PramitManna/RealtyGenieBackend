-- SAFE Migration: Update campaigns table to use persona instead of tones
-- Date: 2025-12-04
-- Description: Replace tones field with persona field for automatic tone mapping

-- Step 1: Check current table structure (run this first to see what exists)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'campaigns' AND table_schema = 'public';

-- Step 2: Add the new persona column
ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS persona TEXT;

-- Step 3: Set default persona for all existing records
UPDATE public.campaigns 
SET persona = 'buyer' 
WHERE persona IS NULL;

-- Step 4: Make persona column NOT NULL after setting defaults
ALTER TABLE public.campaigns ALTER COLUMN persona SET NOT NULL;

-- Step 5: Add check constraint for valid personas
ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_persona_check 
CHECK (persona IN ('buyer', 'seller', 'investor', 'past_client', 'referral', 'cold_prospect'));

-- Step 6: (Optional) Drop the old tones column 
-- ONLY uncomment this line if you're sure you don't need rollback capability
-- ALTER TABLE public.campaigns DROP COLUMN IF EXISTS tones;

-- Step 7: Add documentation
COMMENT ON COLUMN public.campaigns.persona IS 'Target persona for automatic tone mapping (buyer, seller, investor, past_client, referral, cold_prospect)';

-- Step 8: Verify the migration worked
-- SELECT persona, COUNT(*) as count FROM public.campaigns GROUP BY persona;