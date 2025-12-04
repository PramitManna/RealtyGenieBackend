-- Diagnostic Queries for Campaigns Table Migration
-- Run these in Supabase SQL Editor to understand your current setup

-- 1. Check if campaigns table exists and its structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'campaigns' 
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- 2. Count existing campaigns
SELECT COUNT(*) as total_campaigns FROM public.campaigns;

-- 3. Check if tones column exists and sample its values
SELECT 
    id,
    tones,
    pg_typeof(tones) as tones_type
FROM public.campaigns 
LIMIT 5;

-- 4. Check if persona column already exists
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'campaigns' 
              AND column_name = 'persona'
              AND table_schema = 'public'
        ) 
        THEN 'Persona column EXISTS' 
        ELSE 'Persona column MISSING - migration needed'
    END as persona_status;

-- 5. Check constraints on campaigns table
SELECT 
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint 
WHERE conrelid = 'public.campaigns'::regclass;

-- Based on the results above, you'll know:
-- - Whether the campaigns table exists
-- - What columns it currently has
-- - Whether tones is JSONB, TEXT, or another type
-- - Whether persona column already exists
-- - What constraints are already in place