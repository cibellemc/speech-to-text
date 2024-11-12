FROM python:3.12-slim

# Instalação do FFmpeg, biblio de sistema, auxiliares para tratamento de áudio
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libsndfile1 \
    portaudio19-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Atualizar pip
RUN pip install --upgrade pip

# Configurações de diretório
WORKDIR /app

# Instalação de dependências
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Iniciar o servidor
CMD ["streamlit", "run", "streamlit_app.py"]
