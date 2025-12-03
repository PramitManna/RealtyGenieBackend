-- Add conversions table for lead tracking
CREATE TABLE IF NOT EXISTS public.conversions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id UUID REFERENCES public.leads(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'email_response', -- 'email_response', 'phone_call', 'meeting', 'sale', etc.
    value DECIMAL(10,2) DEFAULT 0, -- monetary value if applicable
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create indexes for conversions
CREATE INDEX IF NOT EXISTS idx_conversions_lead_id ON public.conversions(lead_id);
CREATE INDEX IF NOT EXISTS idx_conversions_user_id ON public.conversions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversions_type ON public.conversions(type);

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

-- Grant permissions
GRANT ALL ON public.conversions TO authenticated;