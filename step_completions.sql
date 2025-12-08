-- Create step_completions table for tracking user progress
-- This table stores which steps each user has completed in the onboarding process

CREATE TABLE IF NOT EXISTS step_completions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure one completion record per user per step
    UNIQUE(user_id, step_name)
);

-- Enable Row Level Security (RLS)
ALTER TABLE step_completions ENABLE ROW LEVEL SECURITY;

-- Create policy for users to manage their own step completions
CREATE POLICY "Users can manage their own step completions" ON step_completions
    FOR ALL USING (auth.uid() = user_id);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_step_completions_user_id ON step_completions(user_id);
CREATE INDEX IF NOT EXISTS idx_step_completions_step_name ON step_completions(step_name);
CREATE INDEX IF NOT EXISTS idx_step_completions_user_step ON step_completions(user_id, step_name);

-- Insert some sample data (optional - for testing)
-- INSERT INTO step_completions (user_id, step_name) VALUES 
-- (auth.uid(), 'create-batch'),
-- (auth.uid(), 'import-leads');

COMMENT ON TABLE step_completions IS 'Tracks completion status of onboarding steps for each user';
COMMENT ON COLUMN step_completions.step_name IS 'Identifier for the step (e.g., create-batch, import-leads, setup-automations)';
COMMENT ON COLUMN step_completions.completed_at IS 'When the step was marked as completed (can be updated)';