# Base image
FROM python:3.12

# Instalação do FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Configurações de diretório
WORKDIR /app

# Copia os arquivos necessários
COPY . .

# Instalação de dependências
RUN pip install -r requirements.txt

# Instalação do pyannote-audio diretamente do repositório GitHub
RUN pip install -q git+https://github.com/pyannote/pyannote-audio

# Comando de inicialização
CMD ["streamlit", "run", "streamlit_app.py"]
