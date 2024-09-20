<h1 align="center"> Dashboard para transcrição de áudio </h1>

<p align="center">
Projeto base: https://github.com/jojojaeger/whisper-streamlit
</p>
<br>

<!-- pasta para o git conseguir acessar a foto -->
<p align="center">
  <img alt="Imagem da tela base do dashboard de transcrição de áudios" src=".github/dashboard-transcricao.png" width="100%">
</p>

## 🚀 Tecnologias
- Streamlit: para a criação do web app.
- [Whisper - OpenAI](https://github.com/openai/whisper): modelo de machine learning para reconhecimento e transcrição de voz.
- [WhisperX - m-bain](https://github.com/m-bain/whisperX): modelo otimizado, com função de rotulação de falantes.

## 💻 Atualizações
- Parâmetro n_mels: no método whisper.log_mel_spectrogram define o número de filtros de Mel (ou bandas de frequências) que serão gerados a partir do áudio. Para o modelo large, o n_mels esperado é 128, enquanto para os modelos de tiny à medium, 80.
- Remover funções de transcrição para o inglês e representação de pausas: se mostram desnecessárias ao contexto.
- Acréscimo da diarização do áudio: uso de [pyannote-audio](https://github.com/pyannote/pyannote-audio) ou whisperX para identificação dos falantes.
- Modificação do layout para mostrar processamento.
- Exibir o áudio depois do upload: útil para conferência.
