from auth import authenticated_only
from sqlalchemy import text
import streamlit as st
from services.database import conn
import pandas as pd
import io
import docx
from datetime import datetime, timedelta

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

def delete_history_record(user_id, transcription_id=None, minute_id=None):
    with conn.session as session:
        if transcription_id:
            session.execute(
                text("UPDATE transcriptions SET status = FALSE WHERE id = :id AND user_id = :user_id"),
                {"id": transcription_id, "user_id": user_id}
            )
            session.execute(
                text("UPDATE minutes SET status = FALSE WHERE transcription_id = :id AND user_id = :user_id"),
                {"id": transcription_id, "user_id": user_id}
            )
        elif minute_id:
            session.execute(
                text("UPDATE minutes SET status = FALSE WHERE id = :id AND user_id = :user_id"),
                {"id": minute_id, "user_id": user_id}
            )
        session.commit()

def fetch_unified_history(user_id, limit=10, offset=0, search_term=""):
    search_filter = ""
    params = {"user_id": user_id, "limit": limit, "offset": offset}
    
    if search_term:
        search_filter = "AND (audio_name ILIKE :search OR transcription_file_name ILIKE :search OR CAST(created_at - INTERVAL '3 hours' AS TEXT) ILIKE :search)"
        params["search"] = f"%{search_term}%"

    query = text(f"""
        WITH all_entries AS (
            SELECT 
                'automatic' as source,
                t.id as transcription_id,
                m.id as minute_id,
                t.audio_name,
                t.file_name as transcription_file_name,
                m.file_name as minute_file_name,
                t.created_at,
                t.execution_time,
                'Transcrição + Ata' as entry_type,
                t.transcription,
                m.content as minute_content,
                t.model
            FROM transcriptions t
            JOIN minutes m ON t.id = m.transcription_id
            WHERE m.type = 'automatic' AND t.user_id = :user_id AND t.status = TRUE AND m.status = TRUE

            UNION ALL

            SELECT 
                'transcription_only' as source,
                t.id as transcription_id,
                NULL as minute_id,
                t.audio_name,
                t.file_name as transcription_file_name,
                NULL as minute_file_name,
                t.created_at,
                t.execution_time,
                'Apenas Transcrição' as entry_type,
                t.transcription,
                NULL as minute_content,
                t.model
            FROM transcriptions t
            LEFT JOIN minutes m ON t.id = m.transcription_id AND m.type = 'automatic'
            WHERE m.id IS NULL AND t.user_id = :user_id AND t.status = TRUE

            UNION ALL

            SELECT 
                'minute_only' as source,
                NULL as transcription_id,
                m.id as minute_id,
                NULL as audio_name,
                m.file_name as transcription_file_name,
                m.file_name as minute_file_name,
                m.created_at,
                NULL as execution_time,
                'Apenas Ata' as entry_type,
                NULL as transcription,
                m.content as minute_content,
                m.model_ai as model
            FROM minutes m
            WHERE m.transcription_id IS NULL AND m.user_id = :user_id AND m.status = TRUE
        )
        SELECT * FROM all_entries
        WHERE 1=1 {search_filter}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    with conn.session as session:
        result = session.execute(query, params)
        return result.fetchall()

def fetch_history_counts(user_id):
    query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE entry_type = 'Transcrição + Ata') as count_both,
            COUNT(*) FILTER (WHERE entry_type = 'Apenas Transcrição') as count_trans,
            COUNT(*) FILTER (WHERE entry_type = 'Apenas Ata') as count_ata
        FROM (
            SELECT 'Transcrição + Ata' as entry_type FROM transcriptions t JOIN minutes m ON t.id = m.transcription_id WHERE m.type = 'automatic' AND t.user_id = :user_id AND t.status = TRUE AND m.status = TRUE
            UNION ALL
            SELECT 'Apenas Transcrição' FROM transcriptions t LEFT JOIN minutes m ON t.id = m.transcription_id AND m.type = 'automatic' WHERE m.id IS NULL AND t.user_id = :user_id AND t.status = TRUE
            UNION ALL
            SELECT 'Apenas Ata' FROM minutes m WHERE m.transcription_id IS NULL AND m.user_id = :user_id AND m.status = TRUE
        ) sub
    """)
    with conn.session as session:
        result = session.execute(query, {"user_id": user_id}).fetchone()
        return result

def fetch_transcription_by_file_name(user_id, file_name):
    with conn.session as session:
        result = session.execute(
            text("SELECT id FROM transcriptions WHERE user_id = :user_id and file_name = :file_name AND status = TRUE;"),
            {"user_id": user_id, "file_name": file_name},
        ).fetchone()
    return result[0] if result else None

# --- DOCX HELPERS ---

def _build_transcription_docx(text_content, name):
    doc = docx.Document()
    doc.add_heading("Transcrição", level=1)
    doc.add_paragraph(text_content)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def _build_minutes_docx(text_content, name):
    doc = docx.Document()
    doc.add_heading("Ata de Reunião", level=1)
    doc.add_paragraph(text_content)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- UI COMPONENTS ---

def _render_summary_cards(counts):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-title">Transcrição + Ata</div>
                <div class="stat-value" style="color: #00FFCC;">{counts[0] or 0}</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-title">Apenas Transcrição</div>
                <div class="stat-value" style="color: #FFF;">{counts[1] or 0}</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-title">Apenas Ata</div>
                <div class="stat-value" style="color: #FFF;">{counts[2] or 0}</div>
            </div>
        """, unsafe_allow_html=True)


def _render_history_item(item, user_id):
    # Fallback para registros antigos que não tem audio_name ou para atas sem transcrição vinculada
    name = item.audio_name or item.minute_file_name or item.transcription_file_name or "Arquivo sem nome"
    # Ajuste para horário local (UTC-3)
    local_time = item.created_at - timedelta(hours=3)
    date = local_time.strftime("%d %b %Y, %H:%M")
    entry_type = item.entry_type
    model = item.model if item.model else "Híbrido"
    has_trans = bool(item.transcription)
    has_minute = bool(item.minute_content)

    # Unique item key (used to namespace session_state keys)
    item_key = f"{item.transcription_id}_{item.minute_id}"

    with st.container(border=True):
        # Header: metadata + type badge — pure HTML so the badge stays small
        st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <span style="color: #8b949e; font-size: 0.7rem; font-weight: 500;
                             text-transform: uppercase; letter-spacing: 0.05em;">
                    DATA: {date} &nbsp;|&nbsp; MODELO: {model}
                </span>
                <span style="background-color: #333; color: #eee; padding: 0.15rem 0.55rem;
                             border-radius: 20px; font-size: 0.6rem; font-weight: bold;
                             text-transform: uppercase; white-space: nowrap;">
                    {entry_type}
                </span>
            </div>
            <div style="color: #f0f6fc; font-size: 1.05rem; font-weight: 500;
                        margin-bottom: 0.8rem; line-height: 1.4;">
                {name}
            </div>
        """, unsafe_allow_html=True)

        btn_cols = st.columns(4)

        # ── VER ──────────────────────────────────────────────────────────────
        with btn_cols[0]:
            # Use a flag key so the rerun triggered by download_button
            # does NOT re-open the dialog unintentionally.
            if st.button("VER", key=f"view_{item_key}", use_container_width=True):
                st.session_state["open_dialog"] = {
                    "transcription": item.transcription,
                    "minute_content": item.minute_content,
                }
                st.rerun()

        # ── BAIXAR TRANSCRIÇÃO ───────────────────────────────────────────────
        with btn_cols[1]:
            if has_trans:
                # Build the bytes once and cache in session_state so that
                # the download_button rerun does not rebuild (and does not
                # accidentally trigger the dialog check).
                cache_key = f"bytes_trans_{item_key}"
                if cache_key not in st.session_state:
                    st.session_state[cache_key] = _build_transcription_docx(
                        item.transcription, name
                    )
                st.download_button(
                    "BAIXAR TRANS.",
                    data=st.session_state[cache_key],
                    file_name=f"transcricao_{name}.docx",
                    key=f"dl_t_{item_key}",
                    use_container_width=True,
                    # on_click clears the dialog flag so the download rerun
                    # does not accidentally open the dialog
                    on_click=_clear_dialog_flag,
                )

        # ── BAIXAR ATA ───────────────────────────────────────────────────────
        with btn_cols[2]:
            if has_minute:
                cache_key = f"bytes_min_{item_key}"
                if cache_key not in st.session_state:
                    st.session_state[cache_key] = _build_minutes_docx(
                        item.minute_content, name
                    )
                st.download_button(
                    "BAIXAR ATA",
                    data=st.session_state[cache_key],
                    file_name=f"ata_{name}.docx",
                    key=f"dl_m_{item_key}",
                    use_container_width=True,
                    on_click=_clear_dialog_flag,
                )

        # ── DELETAR ──────────────────────────────────────────────────────────
        with btn_cols[3]:
            if st.button(
                "DELETAR",
                key=f"del_{item_key}",
                use_container_width=True,
                type="secondary",
            ):
                delete_history_record(user_id, item.transcription_id, item.minute_id)
                st.toast("Registro deletado")
                st.rerun()


def _clear_dialog_flag():
    """on_click callback: prevents a stale open_dialog from firing after a download rerun."""
    st.session_state.pop("open_dialog", None)


@st.dialog("Detalhes do Arquivo")
def _show_details_dialog(transcription, minute_content):
    if transcription:
        st.markdown("### Transcrição")
        st.text_area("Conteúdo", transcription, height=200, disabled=True, key="dlg_trans")
    if minute_content:
        st.markdown("### Ata")
        st.text_area("Conteúdo", minute_content, height=200, disabled=True, key="dlg_min")
    if st.button("Fechar"):
        st.session_state.pop("open_dialog", None)
        st.rerun()


@authenticated_only
def display_unified_history(user_id):
    # Limpa bytes cacheados também (opcional, mas evita memory leak)
    keys_to_remove = [k for k in st.session_state if k.startswith("bytes_trans_") or k.startswith("bytes_min_")]
    for k in keys_to_remove:
        st.session_state.pop(k, None)
    st.markdown("""
        <style>
            .stat-card {
                background-color: #111;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 1.5rem;
                height: 100%;
            }
            .stat-title { color: #888; font-size: 0.9rem; margin-bottom: 0.5rem; }
            .stat-value { font-size: 2.5rem; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;"><h1 style="margin:0;">Histórico</h1></div>', unsafe_allow_html=True)
    # st.markdown('<p style="color:#888;margin-bottom:2rem;">Visualize e baixe suas transcrições e atas anteriores.</p>', unsafe_allow_html=True)

    counts = fetch_history_counts(user_id)
    _render_summary_cards(counts)

    st.divider()

    st.markdown('<h2 style="margin-bottom:1rem;">Arquivos Recentes</h2>', unsafe_allow_html=True)


    if "hist_page" not in st.session_state:
        st.session_state.hist_page = 0

    search_term = st.text_input("Buscar por nome de arquivo ou data (DD-MM-AAAA)", placeholder="Digite para filtrar")

    limit = 10
    offset = st.session_state.hist_page * limit
    entries = fetch_unified_history(user_id, limit=limit, offset=offset, search_term=search_term)

    if entries:
        for entry in entries:
            _render_history_item(entry, user_id)

        p_col1, _, p_col3 = st.columns([1, 1, 1])
        with p_col1:
            if st.session_state.hist_page > 0:
                if st.button("Página Anterior", use_container_width=True):
                    st.session_state.hist_page -= 1
                    st.rerun()
        with p_col3:
            if len(entries) == limit:
                if st.button("Próxima Página", use_container_width=True):
                    st.session_state.hist_page += 1
                    st.rerun()
    else:
        st.info("Nenhum arquivo encontrado no histórico.")

    # ── Dialog — opened ONLY when the VER button explicitly sets the flag ──
    if "open_dialog" in st.session_state:
        data = st.session_state["open_dialog"]
        _show_details_dialog(data["transcription"], data["minute_content"])


def generate_transcription_docx(segments, file_name):
    """Gera um DOCX formatado para edição: [HH:MM:SS] SPEAKER: Texto"""
    from transcriber import format_timestamp
    doc = docx.Document()
    doc.add_heading('Transcrição para Edição', level=1)
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

def generate_unified_docx(audio_name, summary, segments):
    """Gera um único DOCX contendo a Ata e a Transcrição unificadas"""
    from transcriber import format_timestamp
    doc = docx.Document()
    
    doc.add_heading(f'Ata de Reunião: {audio_name}', level=1)
    doc.add_paragraph(summary)
    
    doc.add_page_break()
    
    doc.add_heading('Transcrição Completa', level=1)
    for seg in segments:
        p = doc.add_paragraph()
        p.add_run(f"{format_timestamp(seg['start'])} {seg['speaker']}: ").bold = True
        p.add_run(seg['text'])
        
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

def main():
    user_id = st.session_state.get("user_id")
    if user_id:
        display_unified_history(user_id)

if __name__ == "__main__":
    main()