-- Debug: Check for constraints that might prevent multiple campaigns per batch
-- Run this in Supabase SQL Editor to diagnose the issue

-- 1. Check all constraints on campaigns table
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'public.campaigns'::regclass;

-- 2. Check for unique indexes that might cause conflicts
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'campaigns' 
  AND schemaname = 'public';

-- 3. Check current campaigns and their batch_ids
SELECT 
    id,
    batch_id,
    subject,
    persona,
    created_at
FROM public.campaigns 
ORDER BY created_at DESC
LIMIT 10;

-- 4. Check if there are any triggers that might interfere
SELECT 
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers 
WHERE event_object_table = 'campaigns';

-- 5. Test a simple insert to see what error occurs
-- (Uncomment and modify with real batch_id to test)
-- INSERT INTO public.campaigns (
--     id, 
--     batch_id, 
--     subject, 
--     body, 
--     persona, 
--     objective, 
--     status, 
--     created_at, 
--     updated_at
-- ) VALUES (
--     gen_random_uuid(),
--     'your-batch-id-here',
--     'Test Campaign 2',
--     'Test body',
--     'buyer',
--     'Test objective',
--     'active',
--     NOW(),
--     NOW()
-- );