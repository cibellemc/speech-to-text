import os
import torch
import whisper
import tempfile
import subprocess
import streamlit as st
from pyannote.core import Segment
from pyannote.audio import Pipeline

@st.cache_resource
def load_models(whisper_model_name, hf_token):
    print("Carregando modelos (isso só deve acontecer uma vez)...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Usando dispositivo: {device}")
    
    whisper_model = whisper.load_model(whisper_model_name, device=device)
    
    # Certifique-se de que o token está seguro (ex: st.secrets)
    pyannote_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", 
        token=hf_token
    )
    if pyannote_pipeline:
        pyannote_pipeline.to(torch.device(device))
    
    print("Modelos carregados.")
    return whisper_model, pyannote_pipeline, device

def convert_to_wav(input_file):
    """Converte qualquer arquivo (áudio ou vídeo) para WAV 16kHz mono com qualidade ideal para transcrição."""
    # Cria arquivo temporário de entrada com a extensão correta
    ext = os.path.splitext(input_file.name)[-1]
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_input.write(input_file.getbuffer())
    temp_input.flush()
    temp_input.close()

    # Cria arquivo temporário de saída WAV
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav.close()

    # Usa ffmpeg para extrair e converter o áudio
    try:
        subprocess.run([
            "ffmpeg", "-i", temp_input.name,
            "-vn",                 # remove vídeo, se existir
            "-acodec", "pcm_s16le",# formato WAV PCM Linear 16-bit
            "-ar", "16000",        # taxa de amostragem 16kHz
            "-ac", "1",            # mono
            temp_wav.name,
            "-y"                   # sobrescreve se necessário
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro na conversão com ffmpeg: {e}")
        return None
    finally:
        if os.path.exists(temp_input.name):
            os.unlink(temp_input.name)

    return temp_wav.name

def transcribe(audio_path, whisper_model_name, hf_token):
    # Transcreve com Whisper
    model, pipeline, device = load_models(whisper_model_name, hf_token)

    result = model.transcribe(audio_path, language="pt")
    segments = result["segments"]

    # === 2. Diariza com pyannote ===
    if pipeline:
        diarization_result = pipeline(audio_path)
        
        # Na versão 4.0+, o resultado pode ser um objeto DiarizeOutput
        # que contém a anotação no atributo .annotation
        annotation = getattr(diarization_result, "annotation", diarization_result)

        # Atribui falante a cada trecho
        for segment in segments:
            start = segment["start"]
            end = segment["end"]
            segment_speaker = "UNKNOWN"
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                if Segment(start, end).intersects(turn):
                    segment_speaker = f"SPEAKER {int(speaker.split('_')[-1]) + 1}" if speaker.startswith("SPEAKER_") else speaker
                    break
            segment["speaker"] = segment_speaker
    else:
        for segment in segments:
            segment["speaker"] = "UNKNOWN"

    # === Agrupamento de falas consecutivas por falante ===
    grouped_output = []
    if segments:
        current_speaker = segments[0].get("speaker", "UNKNOWN")
        current_text = segments[0]["text"].strip()
        current_start = segments[0]["start"]

        for seg in segments[1:]:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg["text"].strip()

            if speaker == current_speaker:
                current_text += " " + text
            else:
                grouped_output.append({
                    "speaker": current_speaker,
                    "text": current_text,
                    "start": current_start
                })
                current_speaker = speaker
                current_text = text
                current_start = seg["start"]

        # Último grupo
        grouped_output.append({
            "speaker": current_speaker,
            "text": current_text,
            "start": current_start
        })

    return grouped_output

def format_timestamp(seconds):
    """Converte segundos em [HH:MM:SS]"""
    td = float(seconds)
    hours = int(td // 3600)
    minutes = int((td % 3600) // 60)
    secs = int(td % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"