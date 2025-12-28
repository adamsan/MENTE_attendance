import streamlit as st

import pandas as pd
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Literal

from jelenlet.process import process
from jelenlet.excel_export import to_excel
from jelenlet.errors import ReportError
from jelenlet.database import Database

CsoportType = Literal["kezdo", "kozep", "halado", "egyeb"]


def run():
    """CLI entry point for the web app."""
    import subprocess
    import sys

    # Run streamlit with the web app
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/jelenlet/web.py", "--server.runOnSave", "true", "--server.port", "8555"])


def add_download_button_xlsx(file: Path):
    # Download button with xlsx file
    if not file.name.endswith("xlsx"):
        return
    with open(file, mode="rb") as f:
        b = BytesIO()
        b.writelines(f.readlines())
    st.download_button("Letöltés", icon="📥", data=b, file_name=file.name)


def copy_to(dir, uploaded_files):
    for file in uploaded_files:
        file_dest = Path(dir) / file.name
        # st.write(file_dest)
        with open(file_dest, "wb") as f:
            f.write(file.getbuffer())


def main():
    st.set_page_config(page_title="MENTE - jelenléti összefoglaló")
    st.write("# MENTE - jelenléti összefoglaló")
    submitted = False

    with st.form("step_1"):
        st.write("### Táblázatok feltöltése")
        level = st.segmented_control("Csoport", ["kezdo", "kozep", "halado", "egyeb"], default="kozep")

        uploaded_files = st.file_uploader("Részvétel", accept_multiple_files=True, type="xlsx")
        with st.popover("Elvárt formátum", type="secondary", icon="❓"):
            st.write("Excel (`.xlsx`) fájlok:")
            st.write("Oszlopok: `Időbélyeg | E-mail-cím | Teljes név | Jössz próbára?`")

        submitted = st.form_submit_button("Feltöltés", icon="📤")

    if submitted:
        st.write(f"Feltöltött fájlok: {len(uploaded_files)}")
        with tempfile.TemporaryDirectory(prefix="tmp_uploaded_files_", dir="./tmp", delete=True) as tmp:
            copy_to(tmp, uploaded_files)
            db = Database()
            try:
                collective_df = process(Path(tmp), db, level)
                collective_df.reset_index(inplace=True)
                output_file_name = Path(tmp).joinpath(f"{level}_proba_osszegzes_{Path(tmp).name}.xlsx")
                to_excel(output_file_name, collective_df)
                add_download_button_xlsx(output_file_name)
            except ReportError:
                new_lines_str = st.text_area("Database:", value="".join(db.read_all_lines()), height="content")
                new_lines = [a + "\n" for a in new_lines_str.split("\n")]
                db.write_all_lines(new_lines)

        for file in uploaded_files:
            st.write(f"- {file.name}")
            st.write(f"{file}")


if __name__ == "__main__":
    main()
