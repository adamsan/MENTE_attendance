from pathlib import Path

DATABASE_FILE = "database.ini"

EMAILS_DB_FILE = Path(__file__).resolve().parents[2].joinpath("data", DATABASE_FILE)


def create_if_not_exists():
    if not EMAILS_DB_FILE.exists():
        EMAILS_DB_FILE.write_text("# TODO: add <email> = <name> lines here\n#Lines beginning with # are comments, they can be removed.\n\n")


def _is_comment(line: str):
    line = line.strip()
    return line.startswith("#") or line.startswith(";")


def read_email_name_database() -> dict[str, str]:
    create_if_not_exists()
    with open(EMAILS_DB_FILE, encoding="utf-8") as f:
        lines = (line.strip() for line in f.readlines() if "[" not in line)  # ignore sections

    lines = (line for line in lines if line)  # ignore empty lines
    uncommented_pairs = (line.split("=") for line in lines if not _is_comment(line))  # ignore comments
    return {k.strip(): v.strip() for k, v in uncommented_pairs}


def db_append(line: str):
    with open(EMAILS_DB_FILE, encoding="utf-8", mode="a") as f:
        print(line, file=f)
