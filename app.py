import time
from auth import authenticated_only
import streamlit as st
import docx
from sqlalchemy import text
from datetime import datetime
import io
import requests
import os
from pages.select import display_transcriptions, fetch_transcription_by_file_name
from pages.login import login
from services.database import conn
from transcriber import convert_to_wav, transcribe

def check_existing_transcription(file_name, whisper_model):
    """Verifica se já existe uma transcrição idêntica no banco de dados"""
    base_name = os.path.splitext(file_name)[0]  # Remove a extensão
    date_suffix = datetime.today().strftime("%d-%m-%y")
    
    # Padrão de nome esperado: NOMEORIGINAL-modelo-DATA.docx
    expected_pattern = f"{base_name}-{whisper_model}-{date_suffix}%"
    
    with conn.session as session:
        result = session.execute(
            text("""
                SELECT file_name, transcription, execution_time 
                FROM transcriptions 
                WHERE file_name LIKE :pattern
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"pattern": expected_pattern}
        )
        return result.fetchone()
    

# def convert_to_mono(audio_file):
#     sound = AudioSegment.from_file(audio_file)
#     if sound.channels > 1:
#         sound = sound.set_channels(1)
    
#     # Salvar o áudio convertido para mono em um buffer BytesIO
#     mono_audio_buffer = io.BytesIO()
#     sound.export(mono_audio_buffer, format="wav")
#     mono_audio_buffer.seek(0)  # Resetar o ponteiro do buffer para o início
#     mono_audio_buffer.name = audio_file.name  # Mantém o nome original do arquivo

#     return mono_audio_buffer

def _style_language_uploader():
    languages = {
        "PT-BR": {
            "button": "Selecionar arquivos",
            "instructions": "Arraste e solte os arquivos aqui",
            "limits": "Limite de 1GB por arquivo | MP4, M4A, MP3, MKV, WAV",
        },
    }

    hide_label = (
        """
        <style>
            div[data-testid="stFileUploader"]>section[data-testid="stFileUploaderDropzone"]>button[data-testid="baseButton-secondary"] {
               color:white;
            }
            # div[data-testid="stFileUploader"]>section[data-testid="stFileUploaderDropzone"]>button[data-testid="baseButton-secondary"]::after {
            #     content: "BUTTON_TEXT";
            #     color:black;
            #     display: block;
            #     position: absolute;
            # }
            div[data-testid="stFileUploaderDropzoneInstructions"]>div>span {
               visibility:hidden;
            }
            div[data-testid="stFileUploaderDropzoneInstructions"]>div>span::after {
               content:"INSTRUCTIONS_TEXT";
               visibility:visible;
               display:block;
            }
             div[data-testid="stFileUploaderDropzoneInstructions"]>div>small {
               visibility:hidden;
            }
            div[data-testid="stFileUploaderDropzoneInstructions"]>div>small::before {
               content:"FILE_LIMITS";
               visibility:visible;
               display:block;
            }
        </style>
        """.replace(
            "BUTTON_TEXT", languages.get("PT-BR").get("button")
        )
        .replace("INSTRUCTIONS_TEXT", languages.get("PT-BR").get("instructions"))
        .replace("FILE_LIMITS", languages.get("PT-BR").get("limits"))
    )

    st.markdown(hide_label, unsafe_allow_html=True)


# def group_speaker_segments(segments):
#     grouped_transcription = []
#     current_speaker = None
#     current_text = ""

#     for segment in segments:
#         speaker = segment["speaker"]
#         text = segment["text"]

#         # Se o falante atual é o mesmo que o anterior, adiciona o texto ao bloco atual
#         if speaker == current_speaker:
#             current_text += " " + text
#         else:
#             # Se o falante é diferente, salva o bloco anterior (se existir) e inicia um novo
#             if current_speaker is not None:
#                 grouped_transcription.append(
#                     {"speaker": current_speaker, "text": current_text.strip()}
#                 )

#             # Atualiza o falante e o texto atual
#             current_speaker = speaker
#             current_text = text

#     # Adiciona o último bloco de texto, se existir
#     if current_speaker is not None:
#         grouped_transcription.append(
#             {"speaker": current_speaker, "text": current_text.strip()}
#         )

#     return grouped_transcription


def save_transcription_to_db(user_id, file_name, transcription_text, model, execution_time):
    with conn.session as session:
        session.execute(
            text("""
                INSERT INTO transcriptions 
                (user_id, file_name, transcription, model, execution_time) 
                VALUES(:user_id, :file_name, :transcription, :model, :execution_time)
            """),
            {
                "user_id": user_id,
                "file_name": file_name,
                "transcription": transcription_text,
                "model": model,
                "execution_time": execution_time,
            },
        )
        session.commit()

# def generate_summary(text_content):
#     try:
#         ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
#         response = requests.post(f'{ollama_host}/api/generate', 
#             json={
#                 "model": "llama2",
#                 "prompt": f"Faça uma ata em português brasileiro a partir da seguinte transcrição: {text_content}. Pense como um advogado, seja direto e conciso.",
#                 "stream": False
#             })
        
#         if response.status_code == 200:
#             return response.json()['response']
#         else:
#             return "Erro ao gerar resumo. Verifique se o servidor Ollama está rodando."
#     except Exception as e:
#         return f"Erro ao conectar com o Ollama: {str(e)}"


# Use o decorator nas suas views:
@authenticated_only
def upload_view():
    st.title("Realize uma nova Transcrição")

    st.markdown(
        "Clique em `Browse files` para buscar no computador o áudio desejado. Você também tem a opção de arrastar e soltar o arquivo para a área de upload."
    )

    st.markdown(
        "Os modelos de transcrição vão do ``tiny`` ao ``large``. Quanto maior a precisão/confiabilidade (mais próximo de ``large``), mais tempo será necessário para processar sua solicitação."
    )

    speaker_colors = {
        "SPEAKER 1": "FF0000",  # Vermelho
        "SPEAKER 2": "00FF00",  # Verde
        "SPEAKER 3": "0000FF",  # Azul
        "SPEAKER 4": "FFFF00",  # Amarelo
        "SPEAKER 5": "FF00FF",  # Magenta
        "SPEAKER 6": "00FFFF",  # Ciano
        "SPEAKER 7": "FFA500",  # Laranja
        "SPEAKER 8": "800080",  # Roxo
        "SPEAKER 9": "808080",  # Cinza
        "SPEAKER 10": "000000",  # Preto
    }

    # Formulário para upload de arquivo e seleção de modelo
    with st.form("input_form"):
        input_file = st.file_uploader(
            "Arquivos de áudio",
            type=["mp4", "m4a", "mp3", "mkv", "wav"],
            accept_multiple_files=False,
        )

        # Permite selecionar o modelo Whisper (de "tiny" a "large").

        whisper_model = st.selectbox(
            "Modelo de Transcriçao",
            options=["tiny", "base", "small", "medium", "large", "turbo"],
            index=5,
        )

        # num_speakers = st.number_input(
        #     "Quantidade de falantes", min_value=1, max_value=10
        # )

        btn_transcribe = st.form_submit_button(label="Iniciar")

    if btn_transcribe:
        if input_file:
            user_id = st.session_state.get("user_id")  # Assumindo que isso é salvo após o login
            file_name = (
                input_file.name
                + "-"
                + whisper_model
                + "-"
                + datetime.today().strftime("%d-%m-%y")
                + ".docx"
            )

            existing_transcription = fetch_transcription_by_file_name( user_id, file_name)

            if existing_transcription is None:
            # Se o usuário clicar em "Iniciar" e houver arquivos carregados, a transcrição será inicializada

                input_file = convert_to_wav(input_file)
                start_time = time.time()

                # print(input_file.name)
                with st.spinner("Transcrevendo o áudio..."):
                    segments = transcribe(input_file, whisper_model)

                end_time = time.time()
                execution_time = end_time - start_time
                # print(execution_time)

                st.success("Transcrição finalizada!")
                st.write(f"Tempo de execução: {execution_time:.2f} segundos")

                # grouped_segments = group_speaker_segments(segments)

                st.markdown("### Transcrição:")

                text_content = ""

                for segment in segments:
                    speaker = segment["speaker"]
                    text = segment["text"]
                    color = speaker_colors.get(speaker, "000000")  # Cor padrão é preto

                    # Exibe o texto colorido
                    st.markdown(
                        f"<span><strong style='color: #{color};'>{speaker}:</strong> {text}</span>",
                        unsafe_allow_html=True,
                    )

                    text_content += f"{speaker}: {text}\n"

                # with st.spinner("Gerando resumo automático..."):
                #     summary = generate_summary(text_content)
                #     st.markdown("### Resumo Automático:")
                #     st.write(summary)

                
                save_transcription_to_db(user_id,
                        file_name, text_content, whisper_model, execution_time
                    )

                # Cria um arquivo docx na memória
                doc = docx.Document()

                # Adiciona os segmentos ao documento com cores
                for segment in segments:
                    speaker = segment["speaker"]
                    text = segment["text"]
                    color = speaker_colors.get(speaker, "000000")  # Cor padrão é preto

                    # Adiciona um parágrafo com a cor do texto
                    paragraph = doc.add_paragraph()

                    # Adiciona o nome do falante em cor
                    speaker_run = paragraph.add_run(f"{speaker}: ")
                    speaker_run.font.color.rgb = docx.shared.RGBColor(
                        int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16)
                    )

                    # Adiciona o texto do falante em preto
                    text_run = paragraph.add_run(text)
                    text_run.font.color.rgb = docx.shared.RGBColor(0, 0, 0)  # Preto

                bio = io.BytesIO()
                doc.save(bio)
                bio.seek(0)

                # Botão para baixar o arquivo transcrito
                st.download_button(
                    label="Baixar Transcrição",
                    data=bio.getvalue(),
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            else:
                st.error("Transcrição já realizada.")
        else:
                st.error("Por favor, selecione um arquivo.")

def main():
    user_id = login()

    if st.session_state.get('authenticated'):
        _style_language_uploader()
        # usuario_logado = st.session_state.get("user_id")
        # print(f"DEBUG: Usuário logado = {usuario_logado}")  # Log no terminal


        # Tudo relacionado à sidebar só aparece se estiver autenticado
        st.sidebar.subheader("Navegação no sistema")
        st.sidebar.markdown(
            "Clique em `Nova transcrição` para realizar transcrição de um novo arquivo. "
            "Caso deseje consultar transcrições já realizadas, clique em `Histórico`."
        )
        st.sidebar.subheader("Download de transcrições")
        st.sidebar.markdown("Clique em ``Baixar Transcrição`` para obter o arquivo em .docx.")

        st.sidebar.divider()
        if st.sidebar.button("Logout"):
            # usuario_logado = st.session_state.get("user_id")
            # print(f"DEBUG: Usuário deslogando")  # Log no terminal
            # st.logout()
            st.session_state.clear()
            st.rerun()

        pages = [
            st.Page(
                upload_view,
                title="Nova transcrição",
                icon=":material/insert_drive_file:",
            ),
            st.Page(
                lambda: display_transcriptions(user_id),
                title="Histórico", 
                icon=":material/history:"
            ),
        ]
    else:

        st.sidebar.empty()
        pages = [
            st.Page(
                login,
                title="Login",
                icon=":material/login:",
            )
        ]

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
