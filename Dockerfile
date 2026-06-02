FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libsndfile1 \
    portaudio19-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# PyTorch CPU-only (~200MB vs ~2GB da versão CUDA)
RUN pip install torch==2.4.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cpu

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN find . -type d -name "__pycache__" -exec rm -rf {} +

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]