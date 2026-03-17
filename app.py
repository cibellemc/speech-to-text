import io
import os
import docx
import time
import requests
import streamlit as st
from datetime import datetime
from views.login import login
from auth import authenticated_only
from transcriber import convert_to_wav, transcribe
from views.select import fetch_transcription_by_file_name, save_transcription_to_db, save_minutes_to_db

def _style_sidebar():
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                padding-top: 1rem;
            }
            .sidebar-card {
                background-color: #1E1E1E;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-top: 2rem;
                border: 1px solid #333;
            }
            .sidebar-card h3 {
                color: #FFF;
                font-size: 1rem;
                margin-bottom: 0.5rem;
            }
            .sidebar-card p {
                color: #888;
                font-size: 0.85rem;
                line-height: 1.2;
            }
        </style>
    """, unsafe_allow_html=True)

def generate_summary(text_content):
    try:
        ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama-server:11434')
        ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '600'))
        
        prompt = f"""
        Com base na transcrição abaixo, redija uma ATA formal em português brasileiro, seguindo estas regras: 
        - Use apenas informações presentes na transcrição.  
        - Seja extremamente conciso.  
        - Linguagem formal, sem opiniões ou interpretações.  
        - Se algum campo não for mencionado na transcrição, omita-o.

        ---
        **Data**: [omitir]  
        **Local**: [omitir]  

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
                "model": "gemma2:9b",
                "prompt": prompt,
                "stream": False,
                "options": { "temperature": 0.2 } 
            },
            timeout=ollama_timeout
        )

        if response.status_code == 200:
            return response.json().get('response', "Resposta vazia do Ollama.")
        else:
            return f"Erro na API: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Erro ao gerar ata: {str(e)}"

def process_audio(input_file, whisper_model, is_automatic):
    user_id = st.session_state.get("user_id")
    try:
        wav_path = convert_to_wav(input_file)
        start_time = time.time()
        
        with st.spinner("Transcrevendo áudio..."):
            hf_token = os.getenv("HF_TOKEN")
            segments = transcribe(wav_path, whisper_model, hf_token)
            
            if not segments:
                st.error("Erro na transcrição.")
                return

            text_content = "\n".join([f"{s['speaker']}: {s['text']}" for s in segments])
            execution_time = time.time() - start_time
            
            date_str = datetime.today().strftime('%d-%m-%y')
            t_file_name = f"transcricao_{input_file.name}_{date_str}.docx"
            
            t_id = save_transcription_to_db(user_id, input_file.name, t_file_name, text_content, whisper_model, execution_time)
            
            if is_automatic:
                with st.spinner("Gerando Ata Automática..."):
                    summary = generate_summary(text_content)
                    m_file_name = f"ata_{input_file.name}_{date_str}.docx"
                    save_minutes_to_db(user_id, t_id, m_file_name, summary, "gemma2:9b", "automatic")
                    
                    st.success("Processamento concluído!")
                    st.markdown("### Ata Gerada:")
                    st.write(summary)
                    
                    from views.select import generate_minutes_docx
                    docx_bio = generate_minutes_docx(input_file.name, summary)
                    st.download_button("Baixar Ata Final", docx_bio, m_file_name)
            else:
                from views.select import generate_transcription_docx
                docx_bio = generate_transcription_docx(segments, t_file_name)
                st.success("Transcrição concluída!")
                st.download_button("Baixar Transcrição para Edição", docx_bio, t_file_name)

        if os.path.exists(wav_path):
            os.unlink(wav_path)
            
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

@authenticated_only
def transcription_plus_ata_view():
    st.title("Transcrição + Ata")
    st.markdown("Gera ambos automaticamente")
    with st.form("auto_form"):
        file = st.file_uploader("Upload de áudio/vídeo", type=["mp4", "m4a", "mp3", "mkv", "wav"])
        model = st.selectbox("Modelo Whisper", options=["tiny", "base", "small", "medium", "large", "turbo"], index=5)
        if st.form_submit_button("Iniciar", use_container_width=True):
            if file: process_audio(file, model, True)
            else: st.error("Selecione um arquivo.")

@authenticated_only
def transcription_only_view():
    st.title("Apenas Transcrição")
    st.markdown("Gera só a transcrição")
    with st.form("trans_form"):
        file = st.file_uploader("Upload de áudio/vídeo", type=["mp4", "m4a", "mp3", "mkv", "wav"])
        model = st.selectbox("Modelo Whisper", options=["tiny", "base", "small", "medium", "large", "turbo"], index=5)
        if st.form_submit_button("Gerar Transcrição", use_container_width=True):
            if file: process_audio(file, model, False)
            else: st.error("Selecione um arquivo.")

@authenticated_only
def ata_only_view():
    st.title("Apenas Ata")
    st.markdown("Upload de transcrição para gerar ata")
    with st.form("ata_form"):
        file = st.file_uploader("Upload de arquivo (.docx ou .txt)", type=["docx", "txt"])
        if st.form_submit_button("Gerar Ata", use_container_width=True):
            if file:
                try:
                    content = ""
                    if file.name.endswith(".docx"):
                        doc = docx.Document(file)
                        content = "\n".join([p.text for p in doc.paragraphs])
                    else:
                        content = file.read().decode("utf-8")
                    
                    with st.spinner("Gerando Ata..."):
                        summary = generate_summary(content)
                        st.success("Ata gerada!")
                        st.write(summary)
                        from views.select import generate_minutes_docx
                        st.download_button("Baixar Ata", generate_minutes_docx(file.name, summary), f"ata_{file.name}")
                except Exception as e:
                    st.error(f"Erro: {e}")
            else: st.error("Selecione um arquivo.")

@authenticated_only
def history_view():
    user_id = st.session_state.get("user_id")
    from views.select import display_unified_history
    display_unified_history(user_id)

def main():
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        login()
    else:
        _style_sidebar()
        
        with st.sidebar:
            st.title(f"Olá, {st.session_state.username}")
            if st.button("Sair", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
            st.divider()

        pages = {
            "MENU PRINCIPAL": [
                st.Page(transcription_plus_ata_view, title="Transcrição + Ata", icon=":material/description:", url_path="transcricao_e_ata"),
                st.Page(transcription_only_view, title="Apenas Transcrição", icon=":material/mic:", url_path="transcricao"),
                st.Page(ata_only_view, title="Apenas Ata", icon=":material/upload:", url_path="ata"),
                st.Page(history_view, title="Histórico", icon=":material/history:", url_path="historico"),
            ]
        }

        pg = st.navigation(pages)
        
        with st.sidebar:
            st.markdown("""
                <div class="sidebar-card">
                    <h3>Como funciona?</h3>
                    <p>Escolha entre gerar transcrição + ata, apenas transcrição, ou apenas ata a partir de uma transcrição editada.</p>
                </div>
            """, unsafe_allow_html=True)

        pg.run()

if __name__ == "__main__":
    main()
