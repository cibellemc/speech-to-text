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

-- Tabela de transcrições (agora com relação ao usuário)
CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    file_name VARCHAR(255),
    transcription TEXT,
    model VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time FLOAT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Índice para melhorar consultas por usuário
CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);