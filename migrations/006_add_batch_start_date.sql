-- Migration: Add start_date to batches table
-- Date: 2025-12-08
-- Description: Track when batch automation starts sending emails

-- Add start_date column
ALTER TABLE public.batches 
ADD COLUMN IF NOT EXISTS start_date TIMESTAMP WITH TIME ZONE;

-- Add index for querying by start date
CREATE INDEX IF NOT EXISTS idx_batches_start_date ON public.batches(start_date);

-- Add comment
COMMENT ON COLUMN public.batches.start_date IS 'When the batch automation begins sending emails';
