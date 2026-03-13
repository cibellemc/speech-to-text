-- Tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    -- email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de transcrições
CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    audio_name VARCHAR(255), -- Nome original do áudio para agrupamento
    file_name VARCHAR(255),  -- Nome formatado do arquivo gerado
    transcription TEXT,
    model VARCHAR(20),
    status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time FLOAT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabela de Atas (vinculadas às transcrições)
CREATE TABLE IF NOT EXISTS minutes (
    id SERIAL PRIMARY KEY,
    transcription_id INTEGER REFERENCES transcriptions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    file_name VARCHAR(255),
    content TEXT,
    model_ai VARCHAR(50), -- ex: 'gemma2', 'qwen2.5'
    type VARCHAR(20),     -- 'automatic' ou 'manual'
    status BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_minutes_transcription_id ON minutes(transcription_id);
CREATE INDEX IF NOT EXISTS idx_minutes_user_id ON minutes(user_id);