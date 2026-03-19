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
from views.select import (
    fetch_transcription_by_file_name, 
    save_transcription_to_db, 
    save_minutes_to_db,
    generate_minutes_docx,
    generate_transcription_docx,
    display_unified_history
)

def _style_sidebar():
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] { padding-top: 1rem; }
            .sidebar-card {
                background-color: #1E1E1E;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-top: 2rem;
                border: 1px solid #333;
            }
            .sidebar-card h3 { color: #FFF; font-size: 1rem; margin-bottom: 0.5rem; }
            .sidebar-card p { color: #888; font-size: 0.85rem; line-height: 1.2; }
        </style>
    """, unsafe_allow_html=True)

def generate_summary(text_content):
    """Gera a ata via Ollama. Levanta Exception em caso de erro para evitar salvamento indevido."""
    try:
        ollama_host = os.getenv('OLLAMA_HOST', 'http://ollama-server:11434')
        ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '600'))
        
        prompt = f"""
        Transcrição da reunião (use APENAS este texto abaixo para gerar a ata — não copie nem inclua este texto na resposta final):

        {text_content}

        Você é um assistente que transcreve e organiza atas de reuniões de forma extremamente fiel e honesta.

        Crie a ATA DE REUNIÃO seguindo RIGOROSAMENTE este modelo e esta ordem exata. 

        REGRAS OBRIGATÓRIAS:
        - NUNCA invente, suponha, deduza ou complete informações que não estejam explícitas na transcrição.
        - Se não houver informação clara sobre algum ponto → use exatamente: [omitir]
        - Seja seco, objetivo e use linguagem formal administrativa em português brasileiro.
        - Não adicione frases de enfeite, introdução, conclusão ou comentários.

        Formato exato (copie exatamente, inclusive os traços e espaços):

        ATA DE REUNIÃO

        Nº da Ata:          ____________________
        Data:               ____________________
        Participantes:      ____________________
        Responsável pela reunião: ____________________
        Hora início:        ____________________
        Hora fim:           ____________________

        Pauta da reunião:   ____________________
        
        Tópicos discutidos:
        • [resumo muito objetivo do que foi efetivamente falado – 1 linha por tópico principal]
        • [omitir] quando não for possível identificar com clareza

        Decisões tomadas durante a reunião:
        • [apenas o que foi dito explicitamente como decidido]
        • [omitir] se não houver decisão clara registrada

        Ações a realizar e etapas seguintes:
        • [Ação descrita] – Responsável: [nome/persona exata dita ou [omitir]] – Prazo: [prazo dito ou [omitir]]
        • [omitir] quando não houver ação clara com responsável e/ou prazo

        Agora processe APENAS o conteúdo da transcrição acima e preencha SOMENTE os campos:
        - Pauta da reunião
        - Tópicos discutidos
        - Decisões tomadas durante a reunião
        - Ações a realizar e etapas seguintes

        Deixe todos os campos do cabeçalho exatamente como estão (com ____________________).

        Responda SOMENTE com a ata formatada, sem nenhuma frase antes ou depois.
        """

        response = requests.post(
            f'{ollama_host}/api/generate',
            json={
                "model": "llama3.2:latest", # Se o erro 500 persistir, considere mudar para llama3.2:3b
                "prompt": prompt,
                "stream": False,
                "options": { "temperature": 0.2 } 
            },
            timeout=ollama_timeout
        )

        if response.status_code == 200:
            summary = response.json().get('response', "").strip()
            if not summary:
                raise Exception("A IA retornou uma resposta vazia.")
            return summary
        else:
            raise Exception(f"Erro na API Ollama ({response.status_code}): {response.text}")

    except Exception as e:
        raise Exception(f"Falha na comunicação com a IA: {str(e)}")

def process_audio(input_file, whisper_model, is_automatic):
    user_id = st.session_state.get("user_id")
    wav_path = None
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
            
            # Salva a transcrição (sempre salva se chegar aqui)
            t_id = save_transcription_to_db(user_id, input_file.name, t_file_name, text_content, whisper_model, execution_time)
            
            if is_automatic:
                with st.spinner("Gerando Ata Automática..."):
                    try:
                        summary = generate_summary(text_content)
                        m_file_name = f"ata_{input_file.name}_{date_str}.docx"
                        
                        # SÓ SALVA A ATA NO DB SE A IA NÃO DER ERRO
                        save_minutes_to_db(user_id, t_id, m_file_name, summary, "llama3.2", "automatic")
                        
                        st.success("Processamento completo!")
                        st.markdown("### Ata Gerada:")
                        st.write(summary)
                        
                        docx_bio = generate_minutes_docx(input_file.name, summary)
                        st.download_button("Baixar Ata Final", docx_bio, m_file_name)
                    except Exception as ai_error:
                        st.error(f"Transcrição concluída, mas a Ata falhou: {ai_error}")
                        st.info("Você pode baixar a transcrição abaixo ou tentar gerar a ata no menu 'Apenas Ata'.")
                        docx_trans = generate_transcription_docx(segments, t_file_name)
                        st.download_button("Baixar Transcrição", docx_trans, t_file_name)
            else:
                docx_bio = generate_transcription_docx(segments, t_file_name)
                st.success("Transcrição concluída!")
                st.download_button("Baixar Transcrição para Edição", docx_bio, t_file_name)

    except Exception as e:
        st.error(f"Erro crítico no processamento: {e}")
    finally:
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)

@authenticated_only
def transcription_plus_ata_view():
    st.title("Realize Transcrição com Ata")
    
    st.markdown(
        "Clique em `Browse files` para buscar no computador o vídeo ou áudio desejado. Você também tem a opção de arrastar e soltar o arquivo para a área de upload."
    )

    st.markdown(
        "Dois arquivos serão gerados: a transcrição e a ata."
    )

    st.markdown(
        "Os modelos de transcrição vão do ``tiny`` ao ``large``. Quanto maior a precisão/confiabilidade (mais próximo de ``large``), mais tempo será necessário para processar sua solicitação. O modelo ``turbo`` é o mais rápido e preciso."
    )

    st.markdown("A ata será gerada em modelo padrão, com campos para preenchimento manual. O modelo de IA usado é o ``llama3.2``.")
    
    if "run_auto" not in st.session_state: st.session_state.run_auto = False

    with st.form("auto_form"):
        file = st.file_uploader("Upload de áudio/vídeo", type=["mp4", "m4a", "mp3", "mkv", "wav"])
        model = st.selectbox("Modelo de transcrição", options=["tiny", "base", "small", "medium", "large", "turbo"], index=5)
        if st.form_submit_button("Iniciar", use_container_width=True):
            if file:
                st.session_state.run_auto = True
                st.session_state.temp_file = file
                st.session_state.temp_model = model
            else: st.error("Selecione um arquivo.")

    if st.session_state.run_auto:
        process_audio(st.session_state.temp_file, st.session_state.temp_model, True)
        st.session_state.run_auto = False

@authenticated_only
def transcription_only_view():
    st.title("Gere apenas Transcrição")
    st.markdown("""
        Clique em `Browse files` para buscar no computador o áudio desejado. 
        Você também tem a opção de arrastar e soltar o arquivo para a área de upload.

        Os modelos de transcrição vão do ``tiny`` ao ``turbo``. 
        Quanto maior a precisão/confiabilidade (mais próximo de turbo/large), mais tempo será necessário para processar sua solicitação.
    """)
    
    if "run_trans" not in st.session_state: st.session_state.run_trans = False

    with st.form("trans_form"):
        file = st.file_uploader("Upload de áudio/vídeo", type=["mp4", "m4a", "mp3", "mkv", "wav"])
        model = st.selectbox("Modelo de transcrição", options=["tiny", "base", "small", "medium", "large", "turbo"], index=5)
        if st.form_submit_button("Gerar Transcrição", use_container_width=True):
            if file:
                st.session_state.run_trans = True
                st.session_state.temp_file = file
                st.session_state.temp_model = model
            else: st.error("Selecione um arquivo.")

    if st.session_state.run_trans:
        process_audio(st.session_state.temp_file, st.session_state.temp_model, False)
        st.session_state.run_trans = False

@authenticated_only
def ata_only_view():
    st.title("Gere apenas Ata")
    st.markdown("""
        Clique em `Browse files` para carregar um arquivo de transcrição (**.docx** ou **.txt**).
        A IA irá processar o conteúdo e gerar uma ata formatada.
    """)
    
    if "run_ata_only" not in st.session_state: st.session_state.run_ata_only = False

    with st.form("ata_form"):
        file = st.file_uploader("Upload de arquivo (.docx ou .txt)", type=["docx", "txt"])
        if st.form_submit_button("Gerar Ata", use_container_width=True):
            if file:
                st.session_state.run_ata_only = True
                st.session_state.temp_ata_file = file
            else: st.error("Selecione um arquivo.")

    if st.session_state.run_ata_only:
        file = st.session_state.temp_ata_file
        try:
            if file.name.endswith(".docx"):
                doc = docx.Document(file)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = file.read().decode("utf-8")
            
            with st.spinner("Gerando Ata..."):
                summary = generate_summary(content)
                m_file_name = f"ata_{file.name}.docx"
                
                # Salva no banco de dados para aparecer no histórico
                save_minutes_to_db(
                    st.session_state.get("user_id"), 
                    None, 
                    m_file_name, 
                    summary, 
                    "llama3.2", 
                    "manual"
                )
                
                st.success("Ata gerada e salva no histórico!")
                st.write(summary)
                st.download_button("Baixar Ata", generate_minutes_docx(file.name, summary), m_file_name)
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            st.session_state.run_ata_only = False

@authenticated_only
def history_view():
    display_unified_history(st.session_state.get("user_id"))

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
            # st.divider()

        pages = {
            "MENU PRINCIPAL": [
                st.Page(transcription_plus_ata_view, title="Transcrição + Ata", icon=":material/description:"),
                st.Page(transcription_only_view, title="Apenas Transcrição", icon=":material/mic:"),
                st.Page(ata_only_view, title="Apenas Ata", icon=":material/upload:"),
                st.Page(history_view, title="Histórico", icon=":material/history:"),
            ]
        }
        st.navigation(pages).run()

if __name__ == "__main__":
    main()