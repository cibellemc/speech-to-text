import os
import torch
import whisper
import tempfile
import subprocess
import streamlit as st
from pyannote.core import Segment
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook

def convert_to_wav(input_file):
    """Converte qualquer arquivo (áudio ou vídeo) para WAV 16kHz mono."""
    ext = os.path.splitext(input_file.name)[-1]

    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_input.write(input_file.getbuffer())
    temp_input.flush()
    temp_input.close()

    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav.close()

    try:
        subprocess.run([
            "ffmpeg", "-i", temp_input.name,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            temp_wav.name,
            "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro na conversão com ffmpeg: {e}")
        return None
    finally:
        if os.path.exists(temp_input.name):
            os.unlink(temp_input.name)

    return temp_wav.name



@st.cache_resource
def load_models(whisper_model_name, hf_token):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Carrega Whisper
    whisper_model = whisper.load_model(whisper_model_name, device=device)

    # Carrega Pipeline Community-1
    pyannote_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1",
        token=hf_token
    )
    if pyannote_pipeline:
        pyannote_pipeline.to(torch.device(device))

    return whisper_model, pyannote_pipeline, device

def transcribe(audio_path, whisper_model_name, hf_token):
    model, pipeline, device = load_models(whisper_model_name, hf_token)

    # 1. Transcrição com Whisper
    result = model.transcribe(audio_path, language="pt", fp16=(device == "cuda"))
    segments = result["segments"]

    # 2. Diarização com Community-1
    if pipeline:
        # Usando o ProgressHook conforme a nova documentação
        with ProgressHook() as hook:
            diarization_output = pipeline(audio_path, hook=hook)
        
        for segment in segments:
            audio_segment = Segment(segment["start"], segment["end"])
            speakers_in_segment = []
            
            # Ajuste crucial: iterar sobre .speaker_diarization (retorna turn, speaker)
            for turn, speaker in diarization_output.speaker_diarization:
                intersection = audio_segment & turn
                if intersection:
                    speakers_in_segment.append((speaker, intersection.duration))
            
            if speakers_in_segment:
                # Encontra o falante dominante no intervalo do Whisper
                best_speaker = max(speakers_in_segment, key=lambda x: x[1])[0]
                
                # Formatação: de "0" para "SPEAKER 1"
                try:
                    # Alguns modelos retornam int, outros string "0". 
                    # O tratamento abaixo garante o funcionamento de ambos.
                    speaker_id = int(str(best_speaker).split('_')[-1])
                    segment["speaker"] = f"SPEAKER {speaker_id + 1}"
                except:
                    segment["speaker"] = f"SPEAKER {best_speaker}"
            else:
                segment["speaker"] = "UNKNOWN"

    # 3. Agrupamento de falas consecutivas
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
                grouped_output.append({"speaker": current_speaker, "text": current_text, "start": current_start})
                current_speaker, current_text, current_start = speaker, text, seg["start"]
        
        grouped_output.append({"speaker": current_speaker, "text": current_text, "start": current_start})

    return grouped_output


def format_timestamp(seconds):
    """Converte segundos em [HH:MM:SS]"""
    td = float(seconds)
    hours = int(td // 3600)
    minutes = int((td % 3600) // 60)
    secs = int(td % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"