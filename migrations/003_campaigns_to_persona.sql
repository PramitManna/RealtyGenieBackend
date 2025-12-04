-- Migration: Update campaigns table to use persona instead of tones
-- Date: 2025-12-04
-- Description: Replace tones field with persona field for automatic tone mapping

-- First, let's check the current table structure
-- Run this to see what we're working with:
-- SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'campaigns' AND table_schema = 'public';

-- Add the new persona column
ALTER TABLE public.campaigns ADD COLUMN IF NOT EXISTS persona TEXT;

-- Update existing records to use a default persona (simplified approach)
-- Set all existing records to 'buyer' as default persona
UPDATE public.campaigns 
SET persona = 'buyer' 
WHERE persona IS NULL;

-- Make persona column NOT NULL after setting defaults
ALTER TABLE public.campaigns ALTER COLUMN persona SET NOT NULL;

-- Add check constraint for valid personas
ALTER TABLE public.campaigns ADD CONSTRAINT campaigns_persona_check 
CHECK (persona IN ('buyer', 'seller', 'investor', 'past_client', 'referral', 'cold_prospect'));

-- Drop the old tones column (optional - comment out if you want to keep for rollback)
-- ALTER TABLE public.campaigns DROP COLUMN IF EXISTS tones;

-- Add comment explaining the persona field
COMMENT ON COLUMN public.campaigns.persona IS 'Target persona for automatic tone mapping (buyer, seller, investor, past_client, referral, cold_prospect)';