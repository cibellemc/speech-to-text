import os
import streamlit as st
from transcriber import Transcription
import docx
from datetime import datetime
import pathlib
import io
import matplotlib.colors as mcolors

# configurações do streamlit
st.set_page_config(page_title="Whisper", layout="wide", page_icon="💬")

# carregar o estilo css
with open("style.css") as f:
    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

# Barra Lateral (Sidebar) para Upload de Arquivos
with st.sidebar.form("input_form"):
    # Permite que o usuário envie arquivos de áudio nos formatos mp4, m4a, mp3 e wav.
    input_files = st.file_uploader(
        "Arquivos de áudio",
        type=["mp4", "m4a", "mp3", "wav"],
        accept_multiple_files=True,
    )

    # Permite selecionar o modelo Whisper (de "tiny" a "large").
    whisper_model = st.selectbox(
        "Modelo Whisper", options=["tiny", "base", "small", "medium", "large"], index=4
    )

    # Checkbox que ativa a transcrição de pausas (silêncios) no áudio.
    pauses = st.checkbox("Representar pausas na transcrição", value=False)

    # Checkbox para ativar a tradução para o inglês.
    translation = st.checkbox("Tradução para o inglês", value=False)

    # Botão de envio do formulário para iniciar a transcrição.
    transcribe = st.form_submit_button(label="Iniciar")

# Se o usuário clicar em "Iniciar" e houver arquivos carregados, a transcrição será inicializada
if transcribe:
    if input_files:
        st.session_state.transcription = Transcription(
            input_files
        )  # Uma classe que gerencia o processo de transcrição.
        st.session_state.transcription.transcribe(
            whisper_model, translation
        )  # Função para realizar a transcrição com base no modelo selecionado.
    else:
        st.error("Por favor, selecione um arquivo.")

# Se houver uma transcrição, renderize-a. Caso contrário, exiba instruções
if "transcription" in st.session_state:
    for i, output in enumerate(st.session_state.transcription.output):
        doc = docx.Document()
        avg_confidence_score = 0
        amount_words = 0
        save_dir = str(pathlib.Path(__file__).parent.absolute()) + "/transcripts/"

        # Verifica se o diretório existe, caso contrário, cria-o
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        st.markdown(f"#### Transcrição de {output['name']}")
        for idx, segment in enumerate(output["segments"]):
            for w in output["segments"][idx]["words"]:
                amount_words += 1
                avg_confidence_score += w["probability"]
        st.markdown(
            f"_(modelo Whisper:_`{whisper_model}` -  _idioma:_ `{output['language']}` -  _⌀ índice de confiança:_ `{round(avg_confidence_score / amount_words, 3)}`)"
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
                    # pausas maiores que 3 segundos são representadas com reticências
                    if (
                        pauses
                        and prev_word_end != -1
                        and w["start"] - prev_word_end >= 3
                    ):
                        pause = w["start"] - prev_word_end
                        pause_int = int(pause)
                        html_text += f'{"."*pause_int}{{{pause_int}seg}}'
                        text += f'{"."*pause_int}{{{pause_int}seg}}'
                    prev_word_end = w["end"]
                    if color_coding:
                        rgba_color = cmap(w["probability"])
                        rgb_color = tuple(round(x * 255) for x in rgba_color[:3])
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

        if translation:
            with st.expander("Tradução para o inglês"):
                st.markdown(output["translation"], unsafe_allow_html=True)

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

        bio = io.BytesIO()
        doc.save(bio)
        st.download_button(
            label="Baixar Transcrição",
            data=bio.getvalue(),
            file_name=file_name,
            mime="docx",
        )

else:
    # exibir a página de instruções
    st.markdown(
        "<h1>WHISPER - TRANSCRIÇÃO AUTOMÁTICA </h1> <p> Este projeto foi desenvolvido como parte da tese de mestrado de <a href='mailto:johanna.jaeger89@icloud.com'> Johanna Jäger<a/> "
        + "usando o <a href='https://openai.com/blog/whisper'> OpenAI Whisper</a>.</p> <h2 class='highlight'>PRIVACIDADE: </h2> <p>O programa é executado localmente. "
        + "As transcrições são salvas em um diretório local deste computador.</p><h2 class='highlight'>USO: </h2> <ol><li> Selecione os arquivos que deseja transcrever (vários arquivos permitidos)</li>"
        + "<li> Escolha um modelo (<i>large</i> para o melhor resultado) e outros parâmetros, e clique em 'Iniciar'</li> <li> Veja as transcrições geradas na pasta <i>transcripts</i> deste diretório.</li></ol>",
        unsafe_allow_html=True,
    )
