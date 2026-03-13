# FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

# # Instalar Python 3.10 e dependências
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     python3 python3-pip \
#     ffmpeg \
#     git \
#     build-essential \
#     pkg-config \
#     libavcodec-dev \
#     libavformat-dev \
#     libavutil-dev \
#     libswresample-dev \
#     libswscale-dev \
#     libavdevice-dev \
#     libavfilter-dev \
#     libsndfile1 \
#     portaudio19-dev && \
#     apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# # Cria aliases
# RUN ln -sf /usr/bin/python3 /usr/bin/python && \
#     [ -f /usr/bin/pip ] || ln -s /usr/bin/pip3 /usr/bin/pip

# # Atualiza pip
# RUN pip install --upgrade pip

# # Instala PyTorch com suporte a CUDA 12.8
# RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# # Instala ML deps primeiro (ordem importa para resolver conflitos)
# RUN pip install --no-cache-dir \
#     transformers>=4.45.0 \
#     pyannote.audio>=3.3.2

# RUN pip install --no-cache-dir whisperx

# # Diretório da aplicação
# WORKDIR /app

# # Instala restante das dependências
# COPY requirements.txt /app/requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# # Copia o código-fonte
# COPY . .

# # Comando para iniciar o Streamlit
# CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ─── Stage 1: builder ───────────────────────────────────────────
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pip git build-essential \
    libsndfile1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    [ -f /usr/bin/pip ] || ln -s /usr/bin/pip3 /usr/bin/pip

RUN pip install --upgrade pip

RUN pip install --no-cache-dir \
    torch torchaudio --index-url https://download.pytorch.org/whl/cu128

RUN pip install --no-cache-dir \
    transformers>=4.45.0 \
    pyannote.audio>=3.3.2

RUN pip install --no-cache-dir whisperx

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ─── Stage 2: runtime ───────────────────────────────────────────
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pip \
    ffmpeg \
    libsndfile1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    [ -f /usr/bin/pip ] || ln -s /usr/bin/pip3 /usr/bin/pip

# Copia só os pacotes instalados, sem ferramentas de build
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]