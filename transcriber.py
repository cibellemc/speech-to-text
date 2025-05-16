import whisper
import subprocess
import tempfile
from pyannote.audio import Pipeline
from pyannote.core import Segment

def convert_to_wav(input_file):
    """Converte qualquer arquivo (áudio ou vídeo) para WAV 16kHz mono."""
    # Cria arquivo temporário de entrada
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".input")
    temp_input.write(input_file.getbuffer())
    temp_input.flush()
    temp_input.close()

    # Cria arquivo temporário de saída WAV
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav.close()

    # Usa ffmpeg para extrair e converter o áudio
    subprocess.call([
        "ffmpeg", "-i", temp_input.name,
        "-ar", "16000",  # taxa de amostragem 16kHz
        "-ac", "1",      # mono
        temp_wav.name,
        "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return temp_wav.name


def transcribe(input_file, whisper_model):
    # Converte para WAV (aceita vídeo e áudio)
    # audio_path = convert_to_wav(input_file)

    # Transcreve com Whisper
    model = whisper.load_model(whisper_model)
    result = model.transcribe(input_file, language="pt")
    segments = result["segments"]

    # === 2. Diariza com pyannote ===
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token="hf...")
    diarization_result = pipeline(input_file)

    # Atribui falante a cada trecho
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        segment_speaker = "UNKNOWN"
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            if Segment(start, end).intersects(turn):
                segment_speaker = f"SPEAKER {int(speaker.split('_')[-1]) + 1}" if speaker.startswith("SPEAKER_") else speaker
                break
        segment["speaker"] = segment_speaker

    # === Agrupamento de falas consecutivas por falante ===
    grouped_output = []
    if segments:
        current_speaker = segments[0]["speaker"]
        current_text = segments[0]["text"].strip()

        for seg in segments[1:]:
            speaker = seg["speaker"]
            text = seg["text"].strip()

            if speaker == current_speaker:
                current_text += " " + text
            else:
                grouped_output.append({
                    "speaker": current_speaker,
                    "text": current_text
                })
                current_speaker = speaker
                current_text = text

        # Último grupo
        grouped_output.append({
            "speaker": current_speaker,
            "text": current_text
        })

    return grouped_output
