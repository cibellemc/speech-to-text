-- Migration V2: Separating Transcriptions and Minutes

-- 1. Create the minutes table
CREATE TABLE IF NOT EXISTS minutes (
    id SERIAL PRIMARY KEY,
    transcription_id INTEGER REFERENCES transcriptions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    file_name VARCHAR(255),
    content TEXT,
    model_ai VARCHAR(50), -- e.g., 'gemma2', 'qwen2.5'
    type VARCHAR(20),     -- 'automatic' or 'manual'
    status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 2. Add audio_name to transcriptions for easier grouping (optional but recommended in plan)
ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS audio_name VARCHAR(255);

-- 3. Update execution_time and other metadata as needed
-- (Current schema already has execution_time in transcriptions)

-- 4. Index for performance
CREATE INDEX IF NOT EXISTS idx_minutes_transcription_id ON minutes(transcription_id);
CREATE INDEX IF NOT EXISTS idx_minutes_user_id ON minutes(user_id);
