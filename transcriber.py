import whisper
import os
import subprocess
import torch

from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding

from pyannote.audio import Audio
from pyannote.core import Segment

import wave
import contextlib

from sklearn.cluster import AgglomerativeClustering
import numpy as np

def transcribe(input_file, whisper_model, num_speakers):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Cria um diretório temporário
    temp_dir = "temp_audio_files"
    os.makedirs(temp_dir, exist_ok=True)

    # Salva o arquivo carregado
    temp_audio_path = os.path.join(temp_dir, input_file.name)

    # Salva o arquivo no diretório temporário
    with open(temp_audio_path, "wb") as f:
        f.write(input_file.getbuffer())

    # Converte o arquivo para WAV se necessário
    if temp_audio_path[-3:] != "wav":
        subprocess.call(["ffmpeg", "-i", temp_audio_path, "audio.wav", "-y"])
        temp_audio_path = "audio.wav"

    # Carrega o modelo Whisper
    model = whisper.load_model(whisper_model, device=device)
    result = model.transcribe(temp_audio_path, language="pt")
    segments = result["segments"]

    # Obtém a duração do áudio
    with contextlib.closing(wave.open(temp_audio_path, "r")) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)

    audio = Audio()
    embedding_model = PretrainedSpeakerEmbedding(
        "speechbrain/spkrec-ecapa-voxceleb", device=device
    )

    def segment_embedding(segment):
        start = segment["start"]
        end = min(duration, segment["end"])  # Ajusta o fim do segmento
        clip = Segment(start, end)
        waveform, sample_rate = audio.crop(temp_audio_path, clip)
        return embedding_model(waveform[None])

    # Cria embeddings para cada segmento
    embeddings = np.zeros(shape=(len(segments), 192))
    for i, segment in enumerate(segments):
        embeddings[i] = segment_embedding(segment)

    embeddings = np.nan_to_num(embeddings)

    # Clustering para identificação de falantes
    clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
    labels = clustering.labels_
    
    # Adiciona a informação do falante em cada segmento
    for i in range(len(segments)):
        segments[i]["speaker"] = "SPEAKER " + str(labels[i] + 1)

    return segments  # Retorna os segmentos com transcrição e falantes
