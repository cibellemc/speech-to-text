import time
import streamlit as st
import os
import docx
from sqlalchemy import text
from datetime import datetime
import pathlib
import io
import matplotlib.colors as mcolors
from pages.select import display_transcriptions, fetch_transcription_by_file_name
from transcriber import Transcription
from services.database import conn


def _style_language_uploader():
    languages = {
        "PT-BR": {
            "button": "Selecionar arquivos",
            "instructions": "Arraste e solte os arquivos aqui",
            "limits": "Limite de 1GB por arquivo | MP4, M4A, MP3, WAV",
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


def save_transcription_to_db(file_name, transcription_text, model):
    # Executa a query com os dados passados
    with conn.session as session:
        session.execute(
            text(
                "INSERT INTO transcriptions (file_name, transcription, model) VALUES(:file_name, :transcription, :model);"
            ),
            {
                "file_name": file_name,
                "transcription": transcription_text,
                "model": model,
            },
        )
        session.commit()  # Confirma a transação


def upload_view():
    st.title("Realize uma nova Transcrição")

    st.markdown(
        "Clique em `Browse files` para buscar no computador o áudio desejado. Você também tem a opção de arrastar e soltar o arquivo para a área de upload."
    )

    st.markdown(
        "Os modelos de transcrição vão do ``tiny`` ao ``large``. Quanto maior a precisão/confiabilidade (mais próximo de ``large``), mais tempo será necessário para processar sua solicitação."
    )

    # Formulário para upload de arquivo e seleção de modelo
    with st.form("input_form"):
        input_file = st.file_uploader(
            "Arquivos de áudio",
            type=["mp4", "m4a", "mp3", "wav"],
            accept_multiple_files=False,
        )

        # Permite selecionar o modelo Whisper (de "tiny" a "large").

        whisper_model = st.selectbox(
            "Modelo de Transcriçao",
            options=["tiny", "base", "small", "medium", "large"],
            index=4,
        )

        num_speakers = st.number_input(
            "Quantidade de falantes", min_value=1, max_value=10
        )

        transcribe = st.form_submit_button(label="Iniciar")

    if transcribe:

        # Se o usuário clicar em "Iniciar" e houver arquivos carregados, a transcrição será inicializada
        if input_file:
            # print(input_file.name)
            with st.spinner("Transcrevendo o áudio..."):
                transcription = Transcription(input_file)
                transcription_output = transcription.transcribe(whisper_model, num_speakers)

            st.success("Transcrição finalizada!")

            # Exibe a transcrição colorida
            # st.markdown("### Transcrição:")
            for output in transcription_output:
                # print(output['name'])

                doc = docx.Document()
                save_dir = (
                    str(pathlib.Path(__file__).parent.absolute()) + "/transcripts/"
                )

                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)

                text_content = ""
                html_text = ""

                # Cores de confiança - do vermelho ao verde
                colors = [(0.6, 0, 0), (1, 0.7, 0), (0, 0.6, 0)]
                cmap = mcolors.LinearSegmentedColormap.from_list("my_colormap", colors)

                # Coloração das palavras com base na confiança
                for idx, segment in enumerate(output["segments"]):
                    for w in segment["words"]:
                        rgba_color = cmap(w["probability"])
                        rgb_color = tuple(round(x * 255) for x in rgba_color[:3])
                        html_text += (
                            f"<span style='color:rgb{rgb_color}'>{w['word']}</span> "
                        )

                        text_content += w["word"]

                        # Quebra de linha após pontuação
                        if any(c in w["word"] for c in "!?.") and not any(
                            c.isdigit() for c in w["word"]
                        ):
                            html_text += "<br><br>"
                            text_content += "\n\n"

                with st.container():
                    st.markdown(f"#### Transcrição de {input_file.name}:")
                    st.markdown(html_text, unsafe_allow_html=True)

                doc.add_paragraph(text_content)

                # Salva o arquivo transcrito em um docx
                file_name = (
                    input_file.name
                    + "-"
                    + whisper_model
                    + "-"
                    + datetime.today().strftime("%d-%m-%y")
                    + ".docx"
                )

                # print(file_name)
                doc.save(save_dir + file_name)

                existing_transcription = fetch_transcription_by_file_name(file_name)

                if existing_transcription is None:
                    save_transcription_to_db(file_name, text_content, whisper_model)

                bio = io.BytesIO()
                doc.save(bio)

                # Botão para baixar o arquivo transcrito
                st.download_button(
                    label="Baixar Transcrição",
                    data=bio.getvalue(),
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
        else:
            st.error("Por favor, selecione um arquivo.")


def main():

    _style_language_uploader()

    st.sidebar.subheader("Navegação no sistema")

    st.sidebar.markdown(
        "Clique em `Nova transcrição` para realizar transcrição de um novo arquivo. Caso deseje consultar transcrições já realizadas, clique em `Histórico`."
    )

    st.sidebar.subheader("Download de transcrições")
    st.sidebar.markdown(
        "Clique em ``Baixar Transcrição`` para obter o arquivo em .docx."
    )

    pg = st.navigation(
        [
            st.Page(
                upload_view,
                title="Nova transcrição",
                icon=":material/insert_drive_file:",
            ),
            st.Page(
                display_transcriptions, title="Histórico", icon=":material/history:"
            ),
        ]
    )
    pg.run()


if __name__ == "__main__":
    main()
