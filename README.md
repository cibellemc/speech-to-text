<h1 align="center"> Dashboard para transcrição de áudio </h1>

<!-- pasta para o git conseguir acessar a foto -->
<p align="center">
  <img alt="Imagem da tela base do dashboard de transcrição de áudios" src=".github/dashboard-transcricao-historico.png" width="100%">
</p>

<br>
<p align="center">
Projetos base: 
  <ul>
    <li>https://github.com/jojojaeger/whisper-streamlit</li>
    <li>https://medium.com/@xriteshsharmax/speaker-diarization-using-whisper-asr-and-pyannote-f0141c85d59a</li>
  </ul>
</p>
<br>

## 🚀 Tecnologias
- Streamlit: para a criação do web app.
- [Whisper - OpenAI](https://github.com/openai/whisper): modelo de machine learning para reconhecimento e transcrição de voz.
- [WhisperX - m-bain](https://github.com/m-bain/whisperX): modelo otimizado, com função de rotulação de falantes.

# Configurações do ambiente de desenvolvimento
1. Clonagem do projeto
```
git clone https://github.com/cibellemc/speech-to-text.git
```

2. Instalação das bibliotecas presentes no arquivo requeriments.txt
```
pip install -r requeriments.txt
```

3. Instalação do ffmpeg: https://www.ffmpeg.org/download.html

4. Criação do arquivo .streamlit/secrets.toml, que conterá variáveis sensíveis
```
[connections.postgresql]
dialect = "postgresql"
host = "localhost"
port = "5432"
database = "xxx"
username = "xxx"
password = "xxx"
```

5. Criação da tabela no banco de dados
```
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255),
    transcription TEXT,
    model VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

6. Comando para iniciar a aplicação
```
streamlit run streamlit_app.py
```
