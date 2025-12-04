# Supabase Database Migrations

This directory contains database migration scripts for RealtyGenie. These are **NOT** meant to be deployed to production but should be executed manually in your Supabase SQL Editor.

## How to Apply Migrations

### Production Environment:
1. Log into your [Supabase Dashboard](https://app.supabase.com/)
2. Navigate to your project → SQL Editor
3. Copy the contents of each migration file in order
4. Execute them one by one

### Development/Staging:
Follow the same process for your development Supabase instance.

## Migration Files

### 001_initial_setup.sql
- **Status**: ✅ Should already be applied (initial schema)
- **Purpose**: Creates leads, batches, conversions tables with RLS policies
- **When to run**: Only if you're setting up a fresh database

### 002_add_conversions_table.sql  
- **Status**: ⚠️  Check if needed (may be duplicate of 001)
- **Purpose**: Adds conversions table for lead tracking
- **When to run**: Only if conversions table doesn't exist

### 003_campaigns_to_persona.sql
- **Status**: ❌ **HAS SYNTAX ERROR - USE SAFE VERSION**
- **Purpose**: Updates campaigns table to use persona instead of tones
- **Issue**: Contains malformed array literal error

### 003_campaigns_to_persona_safe.sql
- **Status**: 🔄 **USE THIS VERSION INSTEAD**
- **Purpose**: Safe version that updates campaigns table to use persona
- **Required for**: Automations page persona-to-tone mapping

### diagnostic_campaigns.sql
- **Status**: 🔍 **RUN FIRST**
- **Purpose**: Check your current campaigns table structure
- **When to run**: Before applying any migration to understand current state

## Important Notes

- **Never deploy these files to production**
- **Always backup your database before running migrations**
- **Test migrations on development environment first**
- **Check if tables already exist before running setup scripts**

## Checking Migration Status

Before running any migration, check your current database schema:

```sql
-- Check if tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('leads', 'campaigns', 'conversions', 'batches');

-- Check campaigns table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'campaigns' 
  AND table_schema = 'public';
```

## Next Steps for You

1. **URGENT**: Run `003_campaigns_to_persona.sql` in your Supabase SQL Editor
2. This will enable the persona-to-tone mapping we just implemented
3. After running it, your automations page will work properly