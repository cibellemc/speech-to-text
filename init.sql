CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255),
    transcription TEXT,
    model VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time FLOAT
);
