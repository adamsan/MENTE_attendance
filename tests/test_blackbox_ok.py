import pytest
import os
import pandas as pd
from jelenlet.cli import run_program
from jelenlet.database import Database
from pathlib import Path


def load_xlsx(path: Path):
    return pd.read_excel(path)


@pytest.mark.filterwarnings("ignore:Conditional Formatting extension is not supported:UserWarning")
def test_ok_case():
    # setup
    input_dir = Path("tests/data/ok/input")
    expected_dir = Path("tests/data/ok/expected")
    output_dir = Path("tests/data/ok/actual")
    db_path = Path("tests/data/ok/database.ini")
    db = Database(db_path)
    file_name = "kozep_proba_osszegzes_input.xlsx"

    output_file: Path | None = run_program(input_dir, output_dir, "kozep", db)
    if not output_file:
        raise RuntimeError("Output file was not generated!")

    # tests
    assert db.read_email_name_database() == {}  # Assert: DB is empty

    expected_df = load_xlsx(expected_dir / file_name)
    actual_df = load_xlsx(output_file)
    pd.testing.assert_frame_equal(expected_df, actual_df)  # Assert, generated xlsx is as expected

    # cleanup
    os.remove(output_file)
    os.remove(db_path)


@pytest.mark.filterwarnings("ignore:Conditional Formatting extension is not supported:UserWarning")
def test_name_typo_case():
    # Name variation: based on valid christian names, fixer should guess the correct version, and save it to db.
    # Görbe Tamás - Tamás Görbe

    # setup
    base_dir = Path("tests/data/name_typo")
    input_dir = base_dir / "input"
    output_dir = base_dir / "actual"
    expected_dir = base_dir / "expected"
    db_path = base_dir / "database.ini"

    db = Database(db_path)
    file_name = "kozep_proba_osszegzes_input.xlsx"

    output_file: Path | None = run_program(input_dir, output_dir, "kozep", db)
    if not output_file:
        raise RuntimeError("Output file was not generated!")

    # tests
    assert db.read_email_name_database() == {"gorbe.tamas89@gmail.com": "Görbe Tamás"}  # Assert:

    expected_df = load_xlsx(expected_dir / file_name)
    actual_df = load_xlsx(output_file)
    pd.testing.assert_frame_equal(expected_df, actual_df)  # Assert, generated xlsx is as expected

    # cleanup
    os.remove(output_file)
    os.remove(db_path)
