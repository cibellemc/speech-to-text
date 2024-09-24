import time
import streamlit as st
import os
import docx
from sqlalchemy import text
from datetime import datetime
import pathlib
import io
import matplotlib.colors as mcolors
from transcriber import Transcription
from services.database import conn

# Inicializar conexão com PostgreSQL


def save_transcription_to_db(file_name, transcription_text, language, confidence_score):
    # SQL query para inserir os dados na tabela
    # insert_query = text(
    #     """
    #  (%s, %s, %s, %s);
    # """
    # )

    # Executa a query com os dados passados
    with conn.session as session:
        session.execute(
            text(
                "INSERT INTO transcriptions (file_name, transcription, language, confidence_score) VALUES(:file_name, :transcription, :language, :confidence_score);"
            ),
            {
                "file_name": file_name,
                "transcription": transcription_text,
                "language": language,
                "confidence_score": float(confidence_score),
            },
        )
        session.commit()  # Confirma a transação

    # Executa a query com os dados


def upload_view():
    st.title("Realize uma nova Transcrição")

    # Formulário para upload de arquivo e seleção de modelo
    with st.form("input_form"):
        input_files = st.file_uploader(
            "Arquivos de áudio",
            type=["mp4", "m4a", "mp3", "wav"],
            accept_multiple_files=True,
        )

        # Permite selecionar o modelo Whisper (de "tiny" a "large").
        whisper_model = st.selectbox(
            "Modelo Whisper",
            options=["tiny", "base", "small", "medium", "large"],
            index=4,
        )

        transcribe = st.form_submit_button(label="Iniciar")

    # Se o usuário clicar em "Iniciar" e houver arquivos carregados, a transcrição será inicializada
    if transcribe:
        if input_files:
            st.session_state.transcription = Transcription(
                input_files
            )  # Uma classe que gerencia o processo de transcrição.
            st.session_state.transcription.transcribe(
                whisper_model
            )  # Função para realizar a transcrição com base no modelo selecionado.
        else:
            st.error("Por favor, selecione um arquivo.")

        # Se houver uma transcrição, renderize-a. Caso contrário, exiba instruções
    if "transcription" in st.session_state:
        for i, output in enumerate(st.session_state.transcription.output):
            doc = docx.Document()
            avg_confidence_score = 0
            amount_words = 0
            save_dir = (
                str(pathlib.Path(__file__).parent.absolute()) + "/transcripts/"
            )

            # Verifica se o diretório existe, caso contrário, cria-o
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            st.markdown(f"#### Transcrição de {output['name']}")
            for idx, segment in enumerate(output["segments"]):
                for w in output["segments"][idx]["words"]: amount_words += 1
                avg_confidence_score += w["probability"]
                confidence_score = round(avg_confidence_score / amount_words, 3)
                language = output["language"]

            st.markdown(f"_(modelo Whisper:_`{whisper_model}` -  _idioma:_ `{language}` -  _⌀ índice de confiança:_ `{confidence_score}`)"
                )

            prev_word_end = -1
            text = ""
            html_text = ""

            # cores de confiança - do vermelho ao verde
            colors = [(0.6, 0, 0), (1, 0.7, 0), (0, 0.6, 0)]
            cmap = mcolors.LinearSegmentedColormap.from_list("my_colormap", colors)

            with st.expander("Transcrição"):
                color_coding = st.checkbox(
                    "Codificação das cores",
                    value=False,
                    key={i},
                    help="Codificar uma palavra por cores com base na probabilidade de ela ter sido reconhecida corretamente. A escala de cores varia de verde (alto) a vermelho (baixo).",
                )
                for idx, segment in enumerate(output["segments"]):
                    for w in output["segments"][idx]["words"]:

                        if color_coding:
                            rgba_color = cmap(w["probability"])
                            rgb_color = tuple(
                                round(x * 255) for x in rgba_color[:3]
                            )
                        else:
                            rgb_color = (0, 0, 0)
                        html_text += (
                            f"<span style='color:rgb{rgb_color}'>{w['word']}</span>"
                        )
                        text += w["word"]
                        # inserir uma quebra de linha se houver pontuação
                        if any(c in w["word"] for c in "!?.") and not any(
                            c.isdigit() for c in w["word"]
                        ):
                            html_text += "<br><br>"
                            text += "\n\n"
                st.markdown(html_text, unsafe_allow_html=True)
            doc.add_paragraph(text)

        # salvar a transcrição como docx no diretório local
        file_name = (
            output["name"]
            + "-"
            + whisper_model
            + "-"
            + datetime.today().strftime("%d-%m-%y")
            + ".docx"
        )
        doc.save(save_dir + file_name)

        # Salvar no banco de dados
        save_transcription_to_db(file_name, text, language, confidence_score)

        bio = io.BytesIO()
        doc.save(bio)

        st.download_button(
                        label="Baixar Transcrição",
                        data=bio.getvalue(),
                        file_name=file_name,
                        mime="docx",
                    )


def main():
    upload_view()


if __name__ == "__main__":
    main()
