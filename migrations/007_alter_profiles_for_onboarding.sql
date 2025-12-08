-- Alter profiles table to add onboarding-related fields
-- This migration updates the existing profiles table to support the new onboarding flow

-- Add new columns for onboarding data if they don't exist
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS company_name TEXT,
ADD COLUMN IF NOT EXISTS calendly_link TEXT,
ADD COLUMN IF NOT EXISTS realtor_type TEXT CHECK (realtor_type IN ('solo', 'team', '')),
ADD COLUMN IF NOT EXISTS brokerage_logo_url TEXT,
ADD COLUMN IF NOT EXISTS brand_logo_url TEXT,
ADD COLUMN IF NOT EXISTS brokerage_name TEXT;

-- Update years_in_business column to have a default value
ALTER TABLE public.profiles
ALTER COLUMN years_in_business SET DEFAULT 0;

-- Create or update indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_profiles_company_name ON public.profiles(company_name);
CREATE INDEX IF NOT EXISTS idx_profiles_realtor_type ON public.profiles(realtor_type);
CREATE INDEX IF NOT EXISTS idx_profiles_onboarding_completed ON public.profiles(onboarding_completed);
CREATE INDEX IF NOT EXISTS idx_profiles_phone ON public.profiles(phone);

-- Add comment/documentation for new columns
COMMENT ON COLUMN public.profiles.company_name IS 'Real estate company or brokerage name';
COMMENT ON COLUMN public.profiles.calendly_link IS 'Calendly scheduling link (optional)';
COMMENT ON COLUMN public.profiles.realtor_type IS 'Type of realtor: solo (independent) or team (part of a team brand)';
COMMENT ON COLUMN public.profiles.brokerage_logo_url IS 'URL to brokerage/company logo in storage';
COMMENT ON COLUMN public.profiles.brand_logo_url IS 'URL to brand logo for team realtors';
COMMENT ON COLUMN public.profiles.brokerage_name IS 'Name of the brokerage (required for team realtors)';
COMMENT ON COLUMN public.profiles.markets IS 'Array of markets/cities the realtor operates in';
