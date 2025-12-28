import streamlit as st


def run():
    import streamlit.web.cli as stcli

    stcli.main(["run", "src/jelenlet/web.py", "--server.runOnSave", "true", "--server.port", "8555"])


st.write("jello")
