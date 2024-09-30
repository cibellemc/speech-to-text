import whisper
from tempfile import NamedTemporaryFile
from pyannote.audio import Pipeline
# from pyannote_whisper.utils import diarize_text

pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization",
                                    use_auth_token="your/token")

class Transcription:
    def __init__(self, file):
        self.audio = None
        self.output = []  # Inicializa a variável self.output como uma lista vazia

        with NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(file.getvalue())
            self.audio = tmp_file.name

    def transcribe(self, whisper_model: str, num_speakers: int):
        # Carrega o modelo Whisper
        transcriber = whisper.load_model(whisper_model)

        # Identifica o idioma
        # audio = whisper.load_audio(self.audio)
        # audio = whisper.pad_or_trim(audio)

        # if whisper_model == 'large':
        #     num_mels = 128
        # else:
        #     num_mels = 80
        
        # mel = whisper.log_mel_spectrogram(audio, n_mels=num_mels).to(transcriber.device)
        # _, probs = transcriber.detect_language(mel)
        language = "pt" # max(probs, key=probs.get)

        # Realiza a transcrição
        self.raw_output = transcriber.transcribe(
            self.audio,
            language=language,
            verbose=True,
            word_timestamps=True
        )

        # diarization_result = pipeline(self.audio, num_speakers=num_speakers)
        # # final_result = diarize_text(self.raw_output, diarization_result)

        # print("************")
        # print(diarization_result)

        # Limpa tokens e organiza os dados da transcrição
        self.segments = self.raw_output["segments"]
        for segment in self.raw_output["segments"]:
            del segment["tokens"]

        # self.raw_output.update(name="audio.wav", language=language)
        self.output.append(self.raw_output)

        return self.output