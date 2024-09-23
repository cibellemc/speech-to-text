import streamlit as st

# Initialize connection.
conn = st.connection("postgresql", type="sql")