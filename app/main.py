import streamlit as st

st.set_page_config(page_title="El Niño × Energia", layout="wide")
st.navigation([st.Page("pages/main_page.py", title="Visão geral", default=True)]).run()
