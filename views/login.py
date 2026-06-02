import string
import secrets
import hashlib
import streamlit as st
from sqlalchemy import text
from services.database import conn
from sqlalchemy.exc import IntegrityError

def generate_salt():
    """Gera um salt aleatório para hashing de senha"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

def hash_password(password, salt):
    """Cria um hash seguro da senha usando PBKDF2"""
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

def create_user(username, password):
    """Cria um novo usuário no banco de dados"""
    salt = generate_salt()
    password_hash = hash_password(password, salt)
    
    try:
        with conn.session as session:
            result = session.execute(
                text("""
                    INSERT INTO users (username, password_hash, salt) 
                    VALUES (:username, :password_hash, :salt)
                    RETURNING id
                    """),
                {
                    "username": username,
                    "password_hash": password_hash,
                    "salt": salt
                }
            )
            user_id = result.scalar()
            session.commit()
            # st.success(f"Usuário criado com ID: {user_id}")  # Debug
            return True
    except IntegrityError as e:
        session.rollback()
        if "users_username_key" in str(e.orig):  # Verifica se é erro de username duplicado
            st.error("Usuário já cadastrado.")
        else:
            st.error(f"Erro ao criar usuário: {str(e)}")
        return False
    except Exception as e:
        session.rollback()
        st.error(f"Erro inesperado ao criar usuário: {str(e)}")
        return False

def verify_user(username, password):
    """Verifica as credenciais do usuário"""
    try:
        with conn.session as session:
            result = session.execute(
                text("""
                    SELECT id, password_hash, salt FROM users 
                    WHERE username = :username
                    """),
                {"username": username}
            ).fetchone()
            
            if result:
                user_id, stored_hash, salt = result
                input_hash = hash_password(password, salt)
                
                if secrets.compare_digest(input_hash, stored_hash):
                    return user_id
        return None
    except Exception as e:
        # st.error(f"Erro ao verificar usuário: {str(e)}")
        return None

def login_page():
    """Página de login"""
    st.title("Login")
    
    with st.form("login_form"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user_id = verify_user(username, password)
            if user_id:
                st.session_state['user_id'] = user_id
                st.session_state['username'] = username
                st.session_state['authenticated'] = True
                st.success("Login bem-sucedido!")
                st.rerun()
            else:
                st.error("Credenciais inválidas")

def register_page():
    """Página de registro"""
    st.title("Registrar novo usuário")
    
    # with st.form("register_form"):
    #     username = st.text_input("Nome de usuário")
    #     # email = st.text_input("Email")
    #     password = st.text_input("Senha", type="password")
    #     confirm_password = st.text_input("Confirmar senha", type="password")
    #     submit = st.form_submit_button("Registrar")
        
    #     if submit:
    #         if password != confirm_password:
    #             st.error("As senhas não coincidem")
    #         elif len(password) < 8:
    #             st.error("A senha deve ter pelo menos 8 caracteres")
    #         else:
    #             # if create_user(username, email, password):
    #             if create_user(username, password):

    #                 st.success("Usuário criado com sucesso! Faça login para continuar.")
    st.info("Cadastro de usuários desabilitado. Contate o administrador para criar uma conta.")

def login():
    """Página principal de autenticação"""
    if st.session_state.get('authenticated'):
        return st.session_state['user_id']
    
    """Página principal de autenticação"""
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if not st.session_state['authenticated']:
        tab1, tab2 = st.tabs(["Login", "Registrar"])
        
        with tab1:
            login_page()
        
        with tab2:
            register_page()
        
        st.stop()  # Impede o acesso ao resto do app se não autenticado
    
    return None