from auth import authenticated_only
from sqlalchemy import text
import streamlit as st
from services.database import conn
import pandas as pd


# Função para baixar arquivos DOCX
def download_transcription(file_name, transcription_text, index):
    import io
    import docx

    # Cria um arquivo docx na memória
    doc = docx.Document()
    doc.add_paragraph(transcription_text)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)

    # Botão de download
    st.download_button(
        label="Baixar Transcrição",
        data=bio.getvalue(),
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key=f"download_button_{index}",  # Unique key based on index
    )


# Realiza o SELECT no banco de dados para obter todas as transcrições
def fetch_transcriptions(user_id, limit=10, offset=0):
    query = text("""
        SELECT id, file_name, transcription, model 
        FROM transcriptions 
        WHERE user_id = :user_id
        ORDER BY created_at DESC 
        LIMIT :limit OFFSET :offset
    """)
    
    with conn.session as session:
        result = session.execute(query, {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        })
        return result.fetchall()


def fetch_transcription_by_file_name(user_id, file_name):
    with conn.session as session:
        result = session.execute(
            text("SELECT file_name FROM transcriptions WHERE user_id = :user_id and file_name = :file_name;"),
            {  "user_id": user_id,
                "file_name": file_name,
            },
        ).fetchone()  # Aqui você pega a primeira linha correspondente

    # Se o resultado for encontrado, retorna o valor do 'file_name'
    if result:
        return result[0]  # Retorna o primeiro elemento da tupla
    else:
        return None  # Retorna None se não encontrar o arquivo


# Exibe as transcrições e permite baixar os arquivos
@authenticated_only
def display_transcriptions(user_id):
    st.title("Transcrições para Download")

    st.info(
        "As transcrições são salvas no padrão ``nome_do_audio.mp4-modelo-data_de_upload.docx``. Ao realizar a busca, lembre-se que há separação por hífen."
    )

    # Número de transcrições por página
    items_per_page = 10

    # Inicializa o estado da página se não existir
    if "page" not in st.session_state:
        st.session_state.page = 0

    # Busca as transcrições no banco de dados
    transcriptions_list = fetch_transcriptions(user_id,
        limit=items_per_page, offset=st.session_state.page * items_per_page
    )
    transcriptions_df = pd.DataFrame(transcriptions_list)

    if not transcriptions_df.empty:
        search_term = st.text_input("Buscar por nome de arquivo ou data")

        # Filtra a tabela com base no termo de busca
        filtered_df = transcriptions_df[
            transcriptions_df["file_name"].str.contains(
                search_term, case=False, na=False
            )
        ]

        if not filtered_df.empty:
            # Cabeçalhos da tabela
            # st.markdown("### Lista de Transcrições")
            st.divider()
            cols_header = st.columns(
                [3, 2]
            )  # Configura colunas para Nome, Download, Confiança
            cols_header[0].markdown("**Nome do Arquivo**")
            cols_header[1].markdown("**Download**")
            # cols_header[2].markdown("**Confiabilidade**")

            # Itera por cada transcrição filtrada e exibe na tabela
            for index, row in filtered_df.iterrows():
                file_name = row["file_name"]
                # confidence_score = row["confidence_score"]

                # Cria uma linha com três colunas para cada item
                cols = st.columns([3, 2])  # Mesmo layout das colunas

                # Nome do arquivo
                cols[0].markdown(f"{file_name}")

                # Botão de download
                with cols[1]:
                    download_transcription(file_name, row["transcription"], index)

                # Índice de confiabilidade
                # cols[2].markdown(f"{confidence_score:.2f}")
        else:
            st.warning("Nenhuma transcrição encontrada.")

    else:
        st.warning("Nenhuma transcrição disponível.")

    # Botões de navegação
    col1, col2 = st.columns([3,2])

    with col1:
        if st.session_state.page > 0:
            if st.button("Página Anterior"):
                st.session_state.page -= 1  # Volta uma página
                st.rerun()  # Garante a atualização da página

    with col2:
        if len(transcriptions_df) == items_per_page:
            if st.button("Próxima Página"):
                st.session_state.page += 1  # Avança uma página
                st.rerun()  # Garante a atualização da página


# Função principal do Streamlit
def main():
    display_transcriptions()


if __name__ == "__main__":
    main()
