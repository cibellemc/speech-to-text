<h1 align="center"> Dashboard para Transcrição e Geração de Atas </h1>

<p align="center">
  <img alt="Imagem da tela base do dashboard" src="assets/dashboard-transcricao.png" width="100%">
</p>

## 🎯 Sobre o Projeto
Este dashboard é uma solução completa para transcrição de reuniões, geração automatizada de atas usando IA e gerenciamento de histórico. Ele utiliza modelos de última geração para garantir precisão e facilidade no dia a dia administrativo.

## ✨ Funcionalidades
- **Transcrição de Áudio/Vídeo**: Suporte a diversos formatos (mp4, m4a, mp3, mkv, wav) com identificação de falantes (Diarização).
- **Geração de Atas (AI)**: Criação automática de atas estruturadas a partir das transcrições usando modelos como Gemma2 (via Ollama).
- **Histórico Unificado**: Visualize, busque e baixe transcrições e atas geradas anteriormente em formato DOCX.
- **Diarização**: Identificação automática de quem está falando ("Speaker 0", "Speaker 1").

## 🚀 Tecnologias
- **[Streamlit](https://streamlit.io/)**: Interface web interativa.
- **[Whisper (OpenAI)](https://github.com/openai/whisper)**: Modelo de reconhecimento de fala de alta precisão.
- **[Pyannote.audio](https://github.com/pyannote/pyannote-audio)**: Diarização de falantes.
- **[Ollama](https://ollama.com/)**: Orquestração de LLMs locais (Gemma2) para resumo e geração de atas.
- **[PostgreSQL](https://www.postgresql.org/)**: Armazenamento persistente de transcrições e histórico.
- **[SQLAlchemy](https://www.sqlalchemy.org/)**: ORM para comunicação com o banco de dados.

## 🛠️ Configuração do Ambiente

1. **Clone o repositório**:
   ```bash
   git clone git@github.com:cibellemc/speech-to-text.git
   cd speech-to-text
   ```

2. **Configuração de Variáveis de Ambiente**:
   Crie um arquivo `.env` na raiz do projeto com:
   ```env
   HF_TOKEN=seu_token_huggingface_aqui
   OLLAMA_HOST=http://ollama-server:11434
   ```
   *Nota: O `HF_TOKEN` é necessário para baixar os modelos de diarização do Pyannote.*

3. **Suba os containers (Docker)**:

   **Apenas CPU**:
   ```bash
   docker compose up -d --build
   ```

   **Com GPU NVIDIA**:
   *(Necessário NVIDIA Container Toolkit instalado)*
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d --build
   ```

## 🌐 Acesso
A aplicação estará disponível em `http://localhost:8501`.

## 📜 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
