from auth import authenticated_only
from sqlalchemy import text
import streamlit as st
from services.database import conn
import pandas as pd
import io
import docx
from datetime import datetime

# --- DATABASE OPERATIONS ---

def save_transcription_to_db(user_id, audio_name, file_name, transcription_text, model, execution_time):
    with conn.session as session:
        result = session.execute(
            text("""
                INSERT INTO transcriptions 
                (user_id, audio_name, file_name, transcription, model, execution_time) 
                VALUES(:user_id, :audio_name, :file_name, :transcription, :model, :execution_time)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "audio_name": audio_name,
                "file_name": file_name,
                "transcription": transcription_text,
                "model": model,
                "execution_time": execution_time,
            },
        )
        t_id = result.fetchone()[0]
        session.commit()
        return t_id

def save_minutes_to_db(user_id, transcription_id, file_name, content, model_ai, type_gen):
    with conn.session as session:
        session.execute(
            text("""
                INSERT INTO minutes 
                (user_id, transcription_id, file_name, content, model_ai, type) 
                VALUES(:user_id, :transcription_id, :file_name, :content, :model_ai, :type)
            """),
            {
                "user_id": user_id,
                "transcription_id": transcription_id,
                "file_name": file_name,
                "content": content,
                "model_ai": model_ai,
                "type": type_gen,
            },
        )
        session.commit()

def fetch_transcriptions(user_id, limit=10, offset=0):
    query = text("""
        SELECT id, audio_name, file_name, transcription, model, created_at 
        FROM transcriptions 
        WHERE user_id = :user_id AND status = TRUE
        ORDER BY created_at DESC 
        LIMIT :limit OFFSET :offset
    """)
    with conn.session as session:
        result = session.execute(query, {"user_id": user_id, "limit": limit, "offset": offset})
        return result.fetchall()

def fetch_minutes(user_id, limit=10, offset=0):
    query = text("""
        SELECT m.id, m.file_name, m.content, m.model_ai, m.type, m.created_at, t.audio_name
        FROM minutes m
        LEFT JOIN transcriptions t ON m.transcription_id = t.id
        WHERE m.user_id = :user_id AND m.status = TRUE
        ORDER BY m.created_at DESC 
        LIMIT :limit OFFSET :offset
    """)
    with conn.session as session:
        result = session.execute(query, {"user_id": user_id, "limit": limit, "offset": offset})
        return result.fetchall()

def fetch_transcription_by_file_name(user_id, file_name):
    with conn.session as session:
        result = session.execute(
            text("SELECT id FROM transcriptions WHERE user_id = :user_id and file_name = :file_name AND status = TRUE;"),
            {"user_id": user_id, "file_name": file_name},
        ).fetchone()
    return result[0] if result else None

# --- DOCX UTILITIES ---

def generate_transcription_docx(segments, file_name):
    """Gera um DOCX formatado para edição: [HH:MM:SS] SPEAKER: Texto"""
    from transcriber import format_timestamp
    doc = docx.Document()
    doc.add_heading('Transcrição para Edição', level=1)
    # doc.add_paragraph("Instruções: Altere o nome dos falantes ou o texto conforme necessário. Mantenha o formato [tempo] Nome: Texto.")
    
    for seg in segments:
        p = doc.add_paragraph()
        p.add_run(f"{format_timestamp(seg['start'])} {seg['speaker']}: ").bold = True
        p.add_run(seg['text'])
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

def generate_minutes_docx(audio_name, summary):
    doc = docx.Document()
    doc.add_heading(f'Ata de Reunião: {audio_name}', level=1)
    doc.add_paragraph(summary)
    
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- UI COMPONENTS ---

def deactivate_item(table, user_id, item_id):
    with conn.session as session:
        session.execute(
            text(f"UPDATE {table} SET status = FALSE WHERE id = :id AND user_id = :user_id"),
            {"id": item_id, "user_id": user_id},
        )
        session.commit()

@st.dialog("Confirmar Exclusão")
def confirm_delete_dialog(item_name, item_id, user_id, table):
    st.write(f"Tem certeza que deseja deletar permanentemente '{item_name}'?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirmar", type="primary"):
            deactivate_item(table, user_id, item_id)
            st.session_state.delete_confirmed = True
            st.rerun()
    with col2:
        if st.button("Cancelar"):
            st.session_state.delete_pending = None
            st.rerun()

@authenticated_only
def display_transcriptions(user_id):
    st.title("Histórico de Processamento")
    
    tab_t, tab_m = st.tabs(["Transcrições", "Atas"])
    
    items_per_page = 10
    if "page_t" not in st.session_state: st.session_state.page_t = 0
    if "page_m" not in st.session_state: st.session_state.page_m = 0

    with tab_t:
        t_list = fetch_transcriptions(user_id, limit=items_per_page, offset=st.session_state.page_t * items_per_page)
        if t_list:
            df = pd.DataFrame(t_list)
            for i, row in df.iterrows():
                cols = st.columns([3, 1, 1])
                cols[0].write(f"**{row['file_name']}**\n\nModelo: {row['model']} | Data: {row['created_at'].strftime('%d/%m/%y')}")
                
                # Botão Download
                from transcriber import format_timestamp
                # Re-gera o DOCX em memória (poderia ser cacheado)
                # Nota: Aqui precisaríamos carregar os segmentos se quisermos manter a formatação original.
                # Por simplicidade atual, baixaremos o texto bruto.
                doc = docx.Document()
                doc.add_paragraph(row['transcription'])
                bio = io.BytesIO()
                doc.save(bio)
                cols[1].download_button("Baixar", bio.getvalue(), row['file_name'], key=f"dt_{row['id']}")
                
                if cols[2].button("Deletar", key=f"del_t_{row['id']}"):
                    st.session_state.delete_pending = (row['file_name'], row['id'], "transcriptions")
                    st.rerun()
        else:
            st.info("Nenhuma transcrição encontrada.")

    with tab_m:
        m_list = fetch_minutes(user_id, limit=items_per_page, offset=st.session_state.page_m * items_per_page)
        if m_list:
            df = pd.DataFrame(m_list)
            for i, row in df.iterrows():
                cols = st.columns([3, 1, 1])
                tipo = "Auto" if row['type'] == 'automatic' else "Manual"
                cols[0].write(f"**{row['file_name']}**\n\nÁudio: {row['audio_name']} | IA: {row['model_ai']} | Tipo: {tipo}")
                
                doc = docx.Document()
                doc.add_paragraph(row['content'])
                bio = io.BytesIO()
                doc.save(bio)
                cols[1].download_button("Baixar", bio.getvalue(), row['file_name'], key=f"dm_{row['id']}")
                
                if cols[2].button("Deletar", key=f"del_m_{row['id']}"):
                    st.session_state.delete_pending = (row['file_name'], row['id'], "minutes")
                    st.rerun()
        else:
            st.info("Nenhuma ata encontrada.")

    if st.session_state.get("delete_pending"):
        name, iid, table = st.session_state.delete_pending
        confirm_delete_dialog(name, iid, user_id, table)

    if st.session_state.get("delete_confirmed"):
        st.success("Item removido com sucesso!")
        del st.session_state.delete_confirmed
        del st.session_state.delete_pending
        st.rerun()
def main():
    user_id = st.session_state.get("user_id")
    if user_id:
        display_transcriptions(user_id)

if __name__ == "__main__":
    main()