import streamlit as st

import tempfile
import shutil
import os
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Literal
from datetime import datetime, timedelta


from jelenlet.process import process
from jelenlet.excel_export import to_excel
from jelenlet.errors import ReportError
from jelenlet.database import Database

CsoportType = Literal["kezdo", "kozep", "halado", "egyeb"]
GenerationState = Literal["UPLOAD", "FIX_ERRORS", "DOWNLOAD"]


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
    return st.download_button("Letöltés", icon=":material/download_2:", data=b, file_name=file.name, key="download_xlsx_btn")


def extract_xls(zip_file, dest) -> list[Path]:
    extracted_files: list[Path] = []
    with zipfile.ZipFile(zip_file) as zf:
        for member in zf.namelist():
            if not member.lower().endswith(".xlsx"):
                continue
            dest_file = Path(dest) / Path(member).name  # zip slip protection
            with zf.open(member) as source, open(dest_file, "wb") as target:
                shutil.copyfileobj(source, target)
                extracted_files.append(dest_file)
    return extracted_files


def copy_or_extract_to(dir, uploaded_files) -> list[Path]:
    copied_files: list[Path] = []
    for file in uploaded_files:
        if file.name.lower().endswith("zip"):
            copied_files.extend(extract_xls(file, dir))
        else:
            file_dest = Path(dir) / file.name
            # st.write(file_dest)
            with open(file_dest, "wb") as f:
                f.write(file.getbuffer())
                copied_files.append(file_dest)
    return copied_files


def upload_ui():
    submitted = False
    with st.form("step_1"):
        st.write("### Táblázatok feltöltése")
        level = st.segmented_control("Csoport", ["kezdo", "kozep", "halado", "egyeb"], default="kozep") or "egyeb"
        st.session_state.level = level
        left, right = st.columns([7, 1])
        uploaded_files = left.file_uploader("Részvételi táblázatok", accept_multiple_files=True, type=["xlsx", "zip"])
        with right.popover("", type="tertiary", icon=":material/info:"):
            st.write("Excel (`.xlsx`) fájlok elvárt formája:")
            st.write("Oszlopok: `Időbélyeg | E-mail-cím | Teljes név | Jössz próbára?`")

        submitted = st.form_submit_button("Feltöltés", icon=":material/upload_2:")

    if submitted and uploaded_files and len(uploaded_files) > 0:
        st.write(f"Feltöltött fájlok: {len(uploaded_files)}")
        with tempfile.TemporaryDirectory(prefix="tmp_uploaded_files_", dir="./tmp", delete=False) as tmp:
            xlsx_recieved = copy_or_extract_to(tmp, uploaded_files)
            if len(xlsx_recieved) < 1:
                st.write("Nem találtam .xlsx fájlt a feltöltésben! :( ")
                return
            st.session_state.tmp = tmp
            db = Database(Path(tmp).parent / f"{level}.database.ini")
            st.session_state.db = db
            try_to_generate_report(tmp, db, level)


def try_to_generate_report(tmp, db, level):
    try:
        collective_df, output_file_name = process(Path(tmp), db, level, tmp)
        collective_df.reset_index(inplace=True)
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
        " - A rosszakat kommenteld (legyen előttük `#` jel), vagy töröld\n"
        " - Mentés után görgess le, lehetnek új javítani való értékek"
    )
    with st.form("step_2"):
        # text area can't have key - it will not load it's value properly
        new_lines_str = st.text_area("Database:", value="".join(db.read_all_lines()), height="content")
        new_lines = [a + "\n" for a in new_lines_str.split("\n")]
        saved = st.form_submit_button("Mentés :)", icon=":material/save_as:")
        if saved:
            db.write_all_lines(new_lines)
            level = st.session_state.level
            tmp = st.session_state.tmp
            try_to_generate_report(tmp, db, level)


def download_ui():
    st.write("Mentsd el a létrehozott összesítőt:")
    add_download_button_xlsx(st.session_state.output_file)
    st.dataframe(st.session_state.collective_dataframe)
    st.button("Új feldolgozás", key="new_run_btn", on_click=cleanup, icon=":material/replay:")


def cleanup():
    st.session_state.state = "UPLOAD"
    print(st.session_state.tmp)
    if Path("tmp").absolute() == Path(st.session_state.tmp).parent.absolute():
        shutil.rmtree(st.session_state.tmp)
    else:
        print(f"Session tmp not in ./tmp? Cleanup did not happen... {st.session_state.tmp}")

    # Delete old dirs in ./tmp:
    for child in Path("tmp").iterdir():
        if child.name.startswith("."):  # don't delete dot files, .gitkeep, .gitignore, etc...
            continue
        mtime = child.stat().st_mtime
        age: timedelta = datetime.now() - datetime.fromtimestamp(mtime)
        print(f"{child} age: {age}")
        if age > timedelta(hours=36):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                os.remove(child)


def main():
    st.set_page_config(page_title="MENTE - jelenléti összefoglaló", page_icon="data/mente_logo_32.png")
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
