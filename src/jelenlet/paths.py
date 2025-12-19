from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
POSSIBLE_NAMES_CSV = DATA_DIR / "anyakonyvezheto_utonevek_2019_08.csv"
