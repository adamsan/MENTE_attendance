import streamlit as st

import pandas as pd
import tempfile
import shutil
from io import BytesIO
from pathlib import Path
from typing import Literal
from enum import Enum

from jelenlet.process import process
from jelenlet.excel_export import to_excel
from jelenlet.errors import ReportError
from jelenlet.database import Database

CsoportType = Literal["kezdo", "kozep", "halado", "egyeb"]


GenerationState = Literal["UPLOAD", "FIX_ERRORS", "DOWNLOAD"]


# class State(Enum):
#     UPLOAD = "UPLOAD"
#     FIX_ERRORS = "FIX_ERRORS"
#     DOWNLOAD = "DOWNLOAD"


def run():
    """CLI entry point for the web app."""
    import subprocess
    import sys

    # Run streamlit with the web app
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/jelenlet/web.py", "--server.runOnSave", "true", "--server.port", "8555"])


def add_download_button_xlsx(file: Path) -> bool:
    # Download button with xlsx file
    if not file.name.endswith("xlsx"):
        return False
    with open(file, mode="rb") as f:
        b = BytesIO()
        b.writelines(f.readlines())
    return st.download_button("Letöltés", icon="📥", data=b, file_name=file.name)


def copy_to(dir, uploaded_files):
    for file in uploaded_files:
        file_dest = Path(dir) / file.name
        # st.write(file_dest)
        with open(file_dest, "wb") as f:
            f.write(file.getbuffer())


def upload_ui():
    submitted = False
    if not submitted:
        with st.form("step_1"):
            st.write("### Táblázatok feltöltése")
            level = st.segmented_control("Csoport", ["kezdo", "kozep", "halado", "egyeb"], default="kozep")
            st.session_state.level = level
            left, right = st.columns([7, 1])
            uploaded_files = left.file_uploader("Részvételi táblázatok", accept_multiple_files=True, type="xlsx")
            with right.popover("", type="tertiary", icon="❓"):
                st.write("Excel (`.xlsx`) fájlok elvárt formája:")
                st.write("Oszlopok: `Időbélyeg | E-mail-cím | Teljes név | Jössz próbára?`")

            submitted = st.form_submit_button("Feltöltés", icon="📤")

    if submitted and len(uploaded_files) > 0:
        st.write(f"Feltöltött fájlok: {len(uploaded_files)}")
        with tempfile.TemporaryDirectory(prefix="tmp_uploaded_files_", dir="./tmp", delete=False) as tmp:
            copy_to(tmp, uploaded_files)
            st.session_state.tmp = tmp
            db = Database()
            st.session_state.db = db
            try:
                collective_df = process(Path(tmp), db, level)
                collective_df.reset_index(inplace=True)
                output_file_name = Path(tmp).joinpath(f"{level}_proba_osszegzes_{Path(tmp).name}.xlsx")
                to_excel(output_file_name, collective_df)
                st.session_state.output_file = output_file_name
                st.session_state.collective_dataframe = collective_df
                st.session_state.state = "DOWNLOAD"
                st.rerun()
            except ReportError:
                st.session_state.state = "FIX_ERRORS"
                st.rerun()


def fix_errors_ui():
    db: Database = st.session_state.db
    st.write("## Hibajavítás")
    st.write(
        " - A helyes bejegyzéseket kommenteld ki (töröld ki előlük `#` jelet)\n"
        " - a rosszakat kommenteld (legyen előttük `#` jel), vagy töröld"
    )
    with st.form("step_2"):
        new_lines_str = st.text_area("Database:", value="".join(db.read_all_lines()), height="content")
        new_lines = [a + "\n" for a in new_lines_str.split("\n")]
        saved = st.form_submit_button("Mentés :)")
        if saved:
            db.write_all_lines(new_lines)
            level = st.session_state.level
            tmp = st.session_state.tmp
            try:
                collective_df = process(Path(tmp), db, level)
                collective_df.reset_index(inplace=True)
                output_file_name = Path(tmp).joinpath(f"{level}_proba_osszegzes_{Path(tmp).name}.xlsx")
                to_excel(output_file_name, collective_df)
                st.session_state.output_file = output_file_name
                st.session_state.collective_dataframe = collective_df
                st.session_state.state = "DOWNLOAD"
                st.rerun()
            except ReportError:
                st.session_state.state = "FIX_ERRORS"
                st.rerun()


def download_ui():
    st.write("Mentsd el a létrehozott összesítőt:")
    clicked = add_download_button_xlsx(st.session_state.output_file)
    st.dataframe(st.session_state.collective_dataframe)
    if clicked:
        cleanup()


def cleanup():
    st.session_state.state = "UPLOAD"
    print(st.session_state.tmp)
    if Path("tmp").absolute() == Path(st.session_state.tmp).parent.absolute():
        shutil.rmtree(st.session_state.tmp)
    else:
        print(f"Session tmp not in ./tmp? Cleanup did not happen... {st.session_state.tmp}")
    st.rerun()


def main():
    st.set_page_config(page_title="MENTE - jelenléti összefoglaló")
    st.write("# MENTE - jelenléti összefoglaló")

    if "state" not in st.session_state:
        st.session_state.state = "UPLOAD"

    if st.session_state.state == "UPLOAD":
        upload_ui()
    elif st.session_state.state == "FIX_ERRORS":
        fix_errors_ui()
    elif st.session_state.state == "DOWNLOAD":
        download_ui()


if __name__ == "__main__":
    main()
