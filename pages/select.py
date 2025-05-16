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
        WHERE user_id = :user_id AND status = TRUE
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
            text("SELECT file_name FROM transcriptions WHERE user_id = :user_id and file_name = :file_name AND status = TRUE;"),
            {  "user_id": user_id,
                "file_name": file_name,
            },
        ).fetchone()  # primeira linha correspondente

    # Se o resultado for encontrado, retorna o valor do 'file_name'
    if result:
        return result[0]  # Retorna o primeiro elemento da tupla
    else:
        return None  # Retorna None se não encontrar o arquivo
    
def deactivate_transcription(user_id, transcription_id):
    with conn.session as session:
        session.execute(
            text("""
                UPDATE transcriptions 
                SET status = FALSE 
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": transcription_id,
                "user_id": user_id
            },
        )
        session.commit()

# Função de diálogo para confirmar a exclusão
@st.dialog("Confirmar Exclusão")
def confirm_delete_dialog(file_name, transcription_id, user_id):
    st.write(f"Tem certeza que deseja deletar permanentemente a transcrição '{file_name}'?")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Confirmar", type="primary"):
            deactivate_transcription(user_id, transcription_id)
            st.session_state.delete_confirmed = True
            st.rerun()
    
    with col2:
        if st.button("Cancelar"):
            st.session_state.delete_confirmed = False
            st.rerun()

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

    # Estado para controlar a confirmação de exclusão
    if "delete_pending" not in st.session_state:
        st.session_state.delete_pending = None

    # Busca as transcrições no banco de dados
    transcriptions_list = fetch_transcriptions(
        user_id,
        limit=items_per_page, 
        offset=st.session_state.page * items_per_page
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
            st.divider()
            cols_header = st.columns(3)
            cols_header[0].markdown("**Nome do Arquivo**")
            cols_header[1].markdown("**Download**")
            cols_header[2].markdown("**Delete**")

            # Itera por cada transcrição filtrada e exibe na tabela
            for index, row in filtered_df.iterrows():
                file_name = row["file_name"]
                transcription_id = row["id"]

                # Cria uma linha com três colunas para cada item
                cols = st.columns(3)

                # Nome do arquivo
                cols[0].markdown(f"{file_name}")

                # Botão de download
                with cols[1]:
                    download_transcription(file_name, row["transcription"], index)
                
                # Botão para desativar transcrição
                with cols[2]:
                    if st.button(
                        "Deletar",
                        key=f"delete_button_{index}",
                        help=f"Deletar a transcrição {file_name}"
                    ):
                        # Armazena o item a ser deletado para confirmação
                        st.session_state.delete_pending = (file_name, transcription_id)
                        st.rerun()

            # Mostra o diálogo de confirmação se houver uma exclusão pendente
            if st.session_state.delete_pending:
                file_name, transcription_id = st.session_state.delete_pending
                confirm_delete_dialog(file_name, transcription_id, user_id)

            # Mostra mensagem de sucesso após confirmação
            if "delete_confirmed" in st.session_state:
                if st.session_state.delete_confirmed:
                    st.success(f"Transcrição {file_name} deletada com sucesso!")
                # Limpa os estados
                del st.session_state.delete_pending
                del st.session_state.delete_confirmed
                st.rerun()

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