FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

# Instalar Python 3.10 e dependências
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pip \
    ffmpeg \
    build-essential \
    libsndfile1 \
    portaudio19-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Cria aliases: python → python3, pip → pip3
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Atualiza pip
RUN pip install --upgrade pip

# Instala PyTorch com suporte a CUDA 12.8
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Diretório da aplicação
WORKDIR /app

# Instala dependências da aplicação
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
COPY . .

# Comando para iniciar o Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
