from jelenlet.paths import DATA_DIR
from pathlib import Path

EMAILS_DB_FILE = DATA_DIR.joinpath("database.ini")


class Database:
    def __init__(self, db_file: Path = EMAILS_DB_FILE) -> None:
        self.DB_FILE = db_file
        if not self.DB_FILE.exists():
            self.DB_FILE.write_text(
                "# TODO: add <email> = <name> lines here\n#Lines beginning with # are comments, they can be removed.\n\n"
            )

    def read_email_name_database(self) -> dict[str, str]:
        with open(self.DB_FILE, encoding="utf-8") as f:
            lines = (line.strip() for line in f.readlines() if "[" not in line)  # ignore sections

        lines = (line for line in lines if line)  # ignore empty lines
        # ignore comments and lines not containing =
        uncommented_pairs = (line.split("=") for line in lines if not _is_comment(line) and "=" in line)
        return {k.strip(): v.strip() for k, v in uncommented_pairs}

    def db_append(self, line: str):
        with open(self.DB_FILE, encoding="utf-8", mode="a") as f:
            print(line, file=f)

    def read_all_lines(self):
        with open(self.DB_FILE, encoding="utf-8") as f:
            return f.readlines()

    def write_all_lines(self, lines: list[str]):
        with open(self.DB_FILE, encoding="utf-8", mode="w") as f:
            f.writelines(lines)


def _is_comment(line: str):
    line = line.strip()
    return line.startswith("#") or line.startswith(";")


def db_append(line: str):
    with open(EMAILS_DB_FILE, encoding="utf-8", mode="a") as f:
        print(line, file=f)
