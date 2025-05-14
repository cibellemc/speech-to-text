import whisper
import os
import subprocess

from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding

from pyannote.audio import Audio
from pyannote.core import Segment

import wave
import contextlib

from sklearn.cluster import AgglomerativeClustering
import numpy as np

def transcribe(input_file, whisper_model, num_speakers):
    # Cria um diretório temporário
    temp_dir = "temp_audio_files"
    os.makedirs(temp_dir, exist_ok=True)

    # Salva o arquivo carregado
    temp_audio_path = os.path.join(temp_dir, input_file.name)

    # Salva o arquivo no diretório temporário
    with open(temp_audio_path, "wb") as f:
        f.write(input_file.getbuffer())

    # Converte para WAV se necessário
    if not temp_audio_path.lower().endswith('.wav'):
        subprocess.call(["ffmpeg", "-i", temp_audio_path, "audio.wav", "-y"])
        temp_audio_path = "audio.wav"

    # Transcreve com Whisper
    model = whisper.load_model(whisper_model)
    result = model.transcribe(temp_audio_path, language="pt")
    segments = result["segments"]

    # Se for apenas 1 falante, retorna imediatamente com SPEAKER 1
    if num_speakers == 1:
        for segment in segments:
            segment["speaker"] = "SPEAKER 1"
        return segments

    # Processo de diarização (apenas para num_speakers > 1)
    with contextlib.closing(wave.open(temp_audio_path, "r")) as f:
        duration = f.getnframes() / float(f.getframerate())

    audio = Audio()
    embedding_model = PretrainedSpeakerEmbedding(
        "speechbrain/spkrec-ecapa-voxceleb", 
        device="cpu"
    )

    def segment_embedding(segment):
        start = segment["start"]
        end = min(duration, segment["end"])
        clip = Segment(start, end)
        waveform, _ = audio.crop(temp_audio_path, clip)
        return embedding_model(waveform[None])

    embeddings = np.zeros(shape=(len(segments), 192))
    for i, segment in enumerate(segments):
        embeddings[i] = segment_embedding(segment)

    embeddings = np.nan_to_num(embeddings)
    clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
    
    for i, label in enumerate(clustering.labels_):
        segments[i]["speaker"] = f"SPEAKER {label + 1}"

    return segments