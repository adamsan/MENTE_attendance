import pandas as pd
from jelenlet.cli import run_program
from jelenlet.database import Database
from pathlib import Path


def test_ok_case():
    run_program(Path("tests/data/ok/input"), Path("tests/data/ok/actual"), "kozep", Database(Path("tests/data/ok/database.ini")))
    assert True
