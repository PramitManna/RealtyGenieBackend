# Production Deployment Guide

## Database Migrations

### ⚠️ CRITICAL: Required Migration
**You must run this migration before the persona-to-tone feature works:**

1. Go to [Supabase Dashboard](https://app.supabase.com/) → Your Project → SQL Editor
2. Copy and paste the contents of `migrations/003_campaigns_to_persona.sql`
3. Execute the migration
4. Verify the campaigns table now has a `persona` column

### Migration Files Location
- All migration files are in `/migrations/` directory
- These are **documentation only** - not deployed to production
- Must be executed manually in Supabase SQL Editor

## Production Deployment Checklist

### Backend (FastAPI)
- [ ] Environment variables set in production
- [ ] `requirements.txt` dependencies installed
- [ ] Migration `003_campaigns_to_persona.sql` executed in Supabase
- [ ] Health check endpoint working (`/health`)

### Frontend (Next.js)
- [ ] Build passes (`npm run build`)
- [ ] Environment variables set
- [ ] API endpoints configured correctly

### Database (Supabase)
- [ ] All required tables exist
- [ ] RLS policies configured
- [ ] Migration `003_campaigns_to_persona.sql` applied
- [ ] No references to deprecated `tones` field

## Verifying the Migration

After running the migration, verify it worked:

```sql
-- Check campaigns table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'campaigns' 
  AND table_schema = 'public'
  AND column_name IN ('persona', 'tones');

-- Should show 'persona' column exists and 'tones' doesn't (if you chose to drop it)
```

## Rollback Plan

If you need to rollback the persona migration:

```sql
-- Add tones column back
ALTER TABLE public.campaigns ADD COLUMN tones JSONB DEFAULT '[]';

-- Remove persona column (optional)
-- ALTER TABLE public.campaigns DROP COLUMN persona;
```

## API Endpoints Updated

These endpoints now use `persona` instead of `tones`:
- `POST /api/campaigns/generate-drafts` 
- `POST /api/campaign-emails/generate-month1-emails`
- `POST /api/campaign-emails/regenerate`

## Frontend Changes

- Automations page now uses persona selection only
- No more manual tone selection UI
- Automatic tone mapping based on persona