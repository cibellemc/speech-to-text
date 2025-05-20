import io
import os
import docx
import time
import requests
import streamlit as st
from datetime import datetime
from pages.login import login
from auth import authenticated_only
from transcriber import convert_to_wav, transcribe
from pages.select import display_transcriptions, fetch_transcription_by_file_name, save_transcription_to_db

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


import os
import requests

def generate_summary(text_content):
    try:
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11435')
        
        
        prompt = f"""
        Com base na transcrição abaixo, redija uma ATA formal em português brasileiro, seguindo estas regras: 
        - Use apenas informações presentes na transcrição.  
        - Seja extremamente conciso.  
        - Linguagem formal, sem opiniões ou interpretações.  
        - Se algum campo não for mencionado na transcrição, omita-o.

        ---
        **Data**: [omitir]  
        **Local**: [omitit]  

        **Presentes**:  
        - [omitir]  

        **Pauta**:  
        1. [Item 1 discutido]  
           [..]   

        2. [Item 2 discutido]  
           [...]  

        **Encerramento**:  
        - [Próximos passos ou reunião agendada] 
        ---

        **Transcrição**:  
        {text_content}
        """

        response = requests.post(
            f'{ollama_host}/api/generate',
            json={
                "model": "llama3.2:latest",
                "prompt": prompt,
                "stream": False,
                "options": { "temperature": 0.2 } 
            },
            # timeout=10  # Evita timeout infinito
        )

        if response.status_code == 200:
            return response.json().get('response', "Resposta vazia do Ollama.")
        else:
            return f"Erro na API: {response.status_code} - {response.text}"

    except requests.exceptions.RequestException as e:
        return f"Erro de conexão: {str(e)}"
    except Exception as e:
        return f"Erro inesperado: {str(e)}"


# Use o decorator nas suas views:
@authenticated_only
def upload_view():
    st.title("Realize uma nova Transcrição")
    # st.markdown("Escolha entre fazer upload de um arquivo de áudio ou transcrever em tempo real usando seu microfone.")
    st.markdown("Clique em `Browse files` para buscar no computador o áudio desejado. Você também tem a opção de arrastar e soltar o arquivo para a área de upload.")
    st.markdown("Os modelos de transcrição vão do ``tiny`` ao ``large``. Quanto maior a precisão/confiabilidade (mais próximo de ``large``), mais tempo será necessário para processar sua solicitação.")

    speaker_colors = {
        "SPEAKER 1": "FF0000", "SPEAKER 2": "00FF00", "SPEAKER 3": "0000FF",
        "SPEAKER 4": "FFFF00", "SPEAKER 5": "FF00FF", "SPEAKER 6": "00FFFF",
        "SPEAKER 7": "FFA500", "SPEAKER 8": "800080", "SPEAKER 9": "808080",
        "SPEAKER 10": "000000",
    }

    with st.form("input_form"):
        input_file = st.file_uploader(
            "Arquivos de áudio",
            type=["mp4", "m4a", "mp3", "mkv", "wav"],
            accept_multiple_files=False,
        )

        whisper_model = st.selectbox(
            "Modelo de Transcrição",
            options=["tiny", "base", "small", "medium", "large", "turbo"],
            index=5,
        )

        btn_transcribe = st.form_submit_button(label="Iniciar")

    if btn_transcribe:
        if input_file:
            user_id = st.session_state.get("user_id")
            file_name = (
                f"{input_file.name}-{whisper_model}-"
                f"{datetime.today().strftime('%d-%m-%y')}.docx"
            )

            existing_transcription = fetch_transcription_by_file_name(user_id, file_name)

            if existing_transcription is None:
                try:
                    # Processamento principal
                    input_file = convert_to_wav(input_file)
                    start_time = time.time()

                    # Container para mostrar os resultados
                    result_container = st.container()
                    
                    with st.spinner("Processando áudio e gerando conteúdo..."):
                        # Executa a transcrição
                        segments = transcribe(input_file, whisper_model)
                        
                        # Verifica se a transcrição foi bem-sucedida
                        if not segments or len(segments) == 0:
                            st.error("Falha na transcrição: nenhum segmento foi gerado.")
                            return
                        
                        # Prepara o conteúdo de texto
                        text_content = "\n".join(
                            [f"{segment['speaker']}: {segment['text']}" for segment in segments]
                        )
                        
                        # Gera a ata em paralelo
                        with st.spinner("Gerando resumo automático..."):
                            summary = generate_summary(text_content)
                            
                            # Verifica se a ata foi gerada corretamente
                            if not summary or "Erro" in summary:
                                st.error("Falha na geração da ata. Tente novamente.")
                                return

                    end_time = time.time()
                    execution_time = end_time - start_time

                    # Mostra os resultados no container
                    with result_container:
                        st.success("Processamento concluído com sucesso!")
                        st.write(f"Tempo total de execução: {execution_time:.2f} segundos")
                        
                        # Mostra a transcrição
                        st.markdown("### Transcrição:")
                        for segment in segments:
                            speaker = segment["speaker"]
                            color = speaker_colors.get(speaker, "000000")
                            st.markdown(
                                f"<span><strong style='color: #{color};'>{speaker}:</strong> {segment['text']}</span>",
                                unsafe_allow_html=True,
                            )
                        
                        # Mostra a ata
                        st.markdown("### Resumo Automático:")
                        st.write(summary)

                    # Prepara o conteúdo completo para salvar no banco
                    full_content = f"{text_content}\n\n=== RESUMO EM FORMA DE ATA ===\n\n{summary}"
                    
                    # Salva no banco de dados
                    save_transcription_to_db(
                        user_id, file_name, full_content, whisper_model, execution_time
                    )

                    # Gera o documento Word apenas se tudo estiver OK
                    def generate_document(segments, summary):
                        doc = docx.Document()
                        doc.add_heading('Transcrição Completa', level=1)
                        
                        for segment in segments:
                            speaker = segment["speaker"]
                            color = speaker_colors.get(speaker, "000000")
                            
                            paragraph = doc.add_paragraph()
                            speaker_run = paragraph.add_run(f"{speaker}: ")
                            speaker_run.font.color.rgb = docx.shared.RGBColor(
                                int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16)
                            )
                            text_run = paragraph.add_run(segment["text"])
                            text_run.font.color.rgb = docx.shared.RGBColor(0, 0, 0)
                        
                        doc.add_heading('Ata de Reunião', level=1)
                        doc.add_paragraph(summary)
                        
                        bio = io.BytesIO()
                        doc.save(bio)
                        bio.seek(0)
                        return bio

                    # Gera e disponibiliza o documento para download
                    doc_bytes = generate_document(segments, summary)
                    
                    st.download_button(
                        label="Baixar Transcrição Completa",
                        data=doc_bytes.getvalue(),
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

                except Exception as e:
                    st.error(f"Ocorreu um erro durante o processamento: {str(e)}")
                    st.info("Por favor, tente novamente ou contate o suporte.")
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
