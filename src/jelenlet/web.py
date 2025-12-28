import streamlit as st


def run():
    import streamlit.web.cli as stcli

    stcli.main(["run", "src/jelenlet/web.py", "--server.runOnSave", "true", "--server.port", "8555"])


st.set_page_config(page_title="MENTE - jelenléti összefoglaló")
st.write("# MENTE - jelenléti összefoglaló")
submitted = False
with st.form("step_1"):
    st.write("### Táblázatok feltöltése")
    st.segmented_control("Csoport", ["kezdo", "kozep", "halado", "egyeb"], default="kozep")

    uploaded_files = st.file_uploader("Részvétel", accept_multiple_files=True, type="xlsx")
    with st.popover("Elvárt formátum", type="secondary", icon="❓"):
        st.write("Excel (`.xlsx`) fájlok:")
        st.write("Oszlopok: `Időbélyeg | E-mail-cím | Teljes név | Jössz próbára?`")

    submitted = st.form_submit_button("Feltöltés")
if submitted:
    print(uploaded_files)
