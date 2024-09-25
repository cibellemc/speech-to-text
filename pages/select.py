from sqlalchemy import text
import streamlit as st
from services.database import conn

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
def fetch_transcriptions():
    
    query = "SELECT id, file_name, transcription, language, confidence_score FROM transcriptions;"
    df = conn.query(query, ttl="10m")
    return df

def fetch_transcription_by_file_name(file_name):
    
    query = f"SELECT file_name FROM transcriptions WHERE file_name = {file_name};"
    result = conn.query.fetchone()

    if result:
        return result[0]  # Retorna o primeiro elemento da tupla
    else:
        return None  # Retorna None se não encontrar o arquivo


# Exibe as transcrições e permite baixar os arquivos
def display_transcriptions():
    st.title("Transcrições Disponíveis para Download")

    # Busca as transcrições no banco de dados
    transcriptions_df = fetch_transcriptions()

    if not transcriptions_df.empty:
        # Exibe uma tabela com as transcrições
        # st.dataframe(transcriptions_df[['file_name', 'language', 'confidence_score']])

        # Itera por cada transcrição e cria um botão de download
        for index, row in transcriptions_df.iterrows():
            st.markdown(f"### {row['file_name']}")
            st.markdown(
                f"**Idioma**: {row['language']}, **Confiança**: {row['confidence_score']}"
            )

            # Chama a função para download do arquivo
            download_transcription(row["file_name"], row["transcription"], index)
    else:
        st.warning("Nenhuma transcrição disponível.")


# Função principal do Streamlit
def main():
    display_transcriptions()


if __name__ == "__main__":
    main()
