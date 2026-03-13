import os
import torch
import whisperx
import tempfile
import subprocess
import streamlit as st

@st.cache_resource
def load_models(whisper_model_name, hf_token, device="cuda", compute_type="float16"):
    if device == "cpu":
        compute_type = "int8"
        
    print(f"Carregando modelos WhisperX ({whisper_model_name}) no dispositivo: {device}...")
    
    # 1. Carrega o modelo de transcrição
    model = whisperx.load_model(whisper_model_name, device, compute_type=compute_type)
    
    # 2. Carrega o pipeline de diarização
    # Importante: O token deve ser configurado no Hugging Face
    diarize_model = whisperx.diarize.DiarizationPipeline(
        token=hf_token, device=device
    )
    
    print("Modelos carregados.")
    return model, diarize_model

def convert_to_wav(input_file):
    """Converte qualquer arquivo para WAV 16kHz mono."""
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
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            temp_wav.name, "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro na conversão ffmpeg: {e}")
        return None
    finally:
        if os.path.exists(temp_input.name):
            os.unlink(temp_input.name)

    return temp_wav.name

def transcribe(audio_path, whisper_model_name, hf_token, batch_size=16):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    model, diarize_model = load_models(whisper_model_name, hf_token, device)

    # 1. Transcrever
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=batch_size)
    
    # 2. Alinhar (melhora precisão dos timestamps)
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    
    # 3. Diarização
    diarize_segments = diarize_model(audio)
    
    # 4. Atribuir falantes aos segmentos
    result = whisperx.assign_word_speakers(diarize_segments, result)
    
    # === Agrupamento de falas consecutivas por falante ===
    grouped_output = []
    if result["segments"]:
        current_speaker = result["segments"][0].get("speaker", "UNKNOWN")
        current_text = result["segments"][0]["text"].strip()
        current_start = result["segments"][0]["start"]

        for seg in result["segments"][1:]:
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