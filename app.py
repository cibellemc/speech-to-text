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
from views.select import display_transcriptions, fetch_transcription_by_file_name, save_transcription_to_db, save_minutes_to_db

def _style_language_uploader():
    languages = {
        "PT-BR": {
            "button": "Selecionar arquivos",
            "instructions": "Arraste e solte os arquivos aqui",
            "limits": "Limite de 1GB por arquivo | MP4, M4A, MP3, MKV, WAV",
        },
    }

    # Estilização do File Uploader para Português (Opcional se Streamlit suportar nativamente)
    hide_label = """
    <style>
        div[data-testid="stFileUploader"] label {
            display: none;
        }
    </style>
    """
    st.markdown(hide_label, unsafe_allow_html=True)


def generate_summary(text_content, model_name="gemma2:9b"):
    try:
        # Pega o host e timeout do docker-compose
        ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama-server:11434')
        ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '300'))
        
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
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": { "temperature": 0.2 } 
            },
            timeout=ollama_timeout
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            return f"Erro na API: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Erro ao gerar ata: {str(e)}"

@authenticated_only
def transcription_plus_ata_view():
    st.title("Transcrição + Ata")
    st.markdown("### Transcrição e Ata Automáticos")
    st.info("O áudio será transcrito e uma ata será gerada automaticamente usando o modelo padrão.")

    with st.form("transcription_auto_form"):
        input_file = st.file_uploader("Selecione o arquivo de áudio/vídeo", type=["mp4", "m4a", "mp3", "mkv", "wav"])
        whisper_model = st.selectbox("Modelo Whisper (Transcrição)", options=["tiny", "base", "small", "medium", "large", "turbo"], index=5)
        
        btn_auto = st.form_submit_button("Iniciar Transcrição e Ata", use_container_width=True)

    if btn_auto:
        if not input_file:
            st.error("Por favor, selecione um arquivo.")
        else:
            process_audio(input_file, whisper_model, is_automatic=True)

@authenticated_only
def transcription_only_view():
    st.title("Apenas Transcrição")
    st.markdown("### Gerar Transcrição para Edição")
    st.info("Gera um arquivo DOCX com a transcrição bruta para que você possa revisar antes de gerar a ata.")

    with st.form("transcription_only_form"):
        input_file = st.file_uploader("Selecione o arquivo de áudio/vídeo", type=["mp4", "m4a", "mp3", "mkv", "wav"])
        whisper_model = st.selectbox("Modelo Whisper", options=["tiny", "base", "small", "medium", "large", "turbo"], index=5)
        
        btn_manual = st.form_submit_button("Gerar Transcrição", use_container_width=True)

    if btn_manual:
        if not input_file:
            st.error("Por favor, selecione um arquivo.")
        else:
            process_audio(input_file, whisper_model, is_automatic=False)

@authenticated_only
def ata_only_view():
    st.title("Apenas Ata")
    st.markdown("### Gerar Ata a partir de Transcrição Editada")
    st.info("Faça o upload do arquivo DOCX ou TXT editado para gerar a ata final baseada no seu texto revisado.")
    
    with st.form("minutes_only_form"):
        edited_file = st.file_uploader("Arquivo editado", type=["docx", "txt"])
        ai_model = st.selectbox("Modelo de IA (LLM)", options=["gemma2:9b", "qwen2.5:7b", "llama3.2"], index=0)
        btn_gen_minutes = st.form_submit_button("Gerar Ata Agora", use_container_width=True)
        
    if btn_gen_minutes:
        if not edited_file:
            st.error("Selecione o arquivo editado.")
        else:
            process_edited_file(edited_file, ai_model)

@authenticated_only
def history_view():
    user_id = st.session_state.get("user_id")
    display_transcriptions(user_id)

def process_audio(input_file, whisper_model, is_automatic):
    user_id = st.session_state.get("user_id")
    audio_name = input_file.name
    date_str = datetime.today().strftime('%d-%m-%y')
    
    try:
        with st.spinner("Processando áudio (WhisperX)..."):
            # Converte e Transcreve
            from transcriber import convert_to_wav, transcribe
            wav_path = convert_to_wav(input_file)
            hf_token = os.getenv("HF_TOKEN")
            segments = transcribe(wav_path, whisper_model, hf_token)
            if not segments:
                st.error("Erro na transcrição.")
                return

            text_content = "\n".join([f"{s['speaker']}: {s['text']}" for s in segments])
            t_file_name = f"transcricao_{audio_name}_{whisper_model}_{date_str}.docx"
            
            # Salva Transcrição
            t_id = save_transcription_to_db(user_id, audio_name, t_file_name, text_content, whisper_model, 0)
            
            if is_automatic:
                with st.spinner("Gerando Ata Automática (Ollama)..."):
                    # Usando gemma2:9b como padrão para o fluxo automático
                    summary = generate_summary(text_content, model_name="gemma2:9b") 
                    m_file_name = f"ata_{audio_name}_{date_str}.docx"
                    save_minutes_to_db(user_id, t_id, m_file_name, summary, "gemma2:9b", "automatic")
                    st.success("Transcrição e Ata geradas com sucesso!")
                    st.markdown("### Ata Gerada:")
                    st.write(summary)
            else:
                from views.select import generate_transcription_docx
                docx_bio = generate_transcription_docx(segments, t_file_name)
                st.success("Transcrição concluída! Baixe o arquivo para editar.")
                st.download_button("Baixar Transcrição para Edição", docx_bio, t_file_name)
                
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

def process_edited_file(file, ai_model):
    user_id = st.session_state.get("user_id")
    try:
        content = ""
        if file.name.endswith(".docx"):
            doc = docx.Document(file)
            content = "\n".join([p.text for p in doc.paragraphs])
        else:
            content = file.read().decode("utf-8")
        
        with st.spinner(f"Gerando Ata via {ai_model}..."):
            summary = generate_summary(content, model_name=ai_model)
            m_file_name = f"ata_manual_{file.name}_{datetime.today().strftime('%d-%m-%y')}.docx"
            save_minutes_to_db(user_id, None, m_file_name, summary, ai_model, "manual")
            st.success("Ata gerada com sucesso!")
            st.write(summary)
            
            from views.select import generate_minutes_docx
            docx_bio = generate_minutes_docx(file.name, summary)
            st.download_button("Baixar Ata Final", docx_bio, m_file_name)
            
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")

def main():
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        login()
    else:
        # Configuração da Sidebar
        with st.sidebar:
            st.title(f"Olá, {st.session_state.username}")
            if st.button("Sair", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
            st.divider()
            
        # Definição das Páginas para Navegação
        pg_plus = st.Page(transcription_plus_ata_view, title="Transcrição + Ata", url_path="transcricao_e_ata")
        pg_trans = st.Page(transcription_only_view, title="Apenas Transcrição", url_path="transcricao")
        pg_ata = st.Page(ata_only_view, title="Apenas Ata", url_path="ata")
        pg_history = st.Page(history_view, title="Histórico", url_path="historico")

        # Inicializa a Navegação
        pg = st.navigation({
            "Menu Principal": [pg_plus, pg_trans, pg_ata],
            "Gestão": [pg_history]
        })
        
        pg.run()

if __name__ == "__main__":
    main()
