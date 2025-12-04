-- SQL schema for RealtyGenie Lead Management
-- Run these commands in your Supabase SQL Editor to create the required tables

-- Create leads table
CREATE TABLE IF NOT EXISTS public.leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT,
    phone TEXT,
    address TEXT,
    batch_id UUID REFERENCES public.batches(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'converted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_leads_batch_id ON public.leads(batch_id);
CREATE INDEX IF NOT EXISTS idx_leads_user_id ON public.leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_email ON public.leads(email);

-- Enable RLS (Row Level Security)
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for leads table
CREATE POLICY "Users can view their own leads" ON public.leads
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own leads" ON public.leads
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own leads" ON public.leads
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own leads" ON public.leads
    FOR DELETE USING (auth.uid() = user_id);

-- Create conversions table for tracking lead conversions
CREATE TABLE IF NOT EXISTS public.conversions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id UUID REFERENCES public.leads(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- 'email_response', 'phone_call', 'meeting', 'sale', etc.
    value DECIMAL(10,2), -- monetary value if applicable
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create indexes for conversions
CREATE INDEX IF NOT EXISTS idx_conversions_lead_id ON public.conversions(lead_id);
CREATE INDEX IF NOT EXISTS idx_conversions_user_id ON public.conversions(user_id);

-- Enable RLS for conversions
ALTER TABLE public.conversions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for conversions table
CREATE POLICY "Users can view their own conversions" ON public.conversions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own conversions" ON public.conversions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own conversions" ON public.conversions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own conversions" ON public.conversions
    FOR DELETE USING (auth.uid() = user_id);

-- Update batches table to have proper lead count tracking
-- Add trigger to automatically update lead count in batches table
CREATE OR REPLACE FUNCTION update_batch_lead_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.batches 
        SET lead_count = (
            SELECT COUNT(*) FROM public.leads 
            WHERE batch_id = NEW.batch_id
        )
        WHERE id = NEW.batch_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.batches 
        SET lead_count = (
            SELECT COUNT(*) FROM public.leads 
            WHERE batch_id = OLD.batch_id
        )
        WHERE id = OLD.batch_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS update_batch_count_on_insert ON public.leads;
CREATE TRIGGER update_batch_count_on_insert
    AFTER INSERT ON public.leads
    FOR EACH ROW EXECUTE FUNCTION update_batch_lead_count();

DROP TRIGGER IF EXISTS update_batch_count_on_delete ON public.leads;
CREATE TRIGGER update_batch_count_on_delete
    AFTER DELETE ON public.leads
    FOR EACH ROW EXECUTE FUNCTION update_batch_lead_count();

-- Grant necessary permissions
GRANT ALL ON public.leads TO authenticated;
GRANT ALL ON public.conversions TO authenticated;