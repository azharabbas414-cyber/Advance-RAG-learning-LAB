import streamlit as st
from app.ui import run_app

st.set_page_config(
    page_title="RAG-X | Phase 1",
    page_icon="🧠",
    layout="wide",
)

run_app()
