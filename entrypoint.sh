#!/bin/bash

mkdir -p /app/.streamlit

# Criação do arquivo secrets.toml
cat <<EOF > /app/.streamlit/secrets.toml
[connections.postgresql]
dialect = "postgresql"
host = "${POSTGRES_HOST:-localhost}"
port = "${POSTGRES_PORT:-5432}"
database = "${POSTGRES_DB:-transcritor}"
username = "${POSTGRES_USER:-postgres}"
password = "${POSTGRES_PASSWORD:-12345678}"
EOF

# Iniciar o Streamlit
streamlit run streamlit_app.py
