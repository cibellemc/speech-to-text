# auth.py
from views.login import login
import streamlit as st
import hashlib
import secrets
import string
import functools
from sqlalchemy import text
from services.database import conn

def generate_salt():
    """Gera um salt aleatório para hashing de senha"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

def hash_password(password, salt):
    """Cria um hash seguro da senha usando PBKDF2"""
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

# [Restante das funções de autenticação...]

def authenticated_only(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated'):
            st.warning("Por favor, faça login para acessar esta página")
            login()
            st.stop()
        return func(*args, **kwargs)
    return wrapper