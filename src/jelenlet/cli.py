from pathlib import Path
import argparse

from jelenlet.process import process, CsoportType
from jelenlet.excel_export import to_excel
from jelenlet.errors import ReportError
from jelenlet.database import Database


def main():
    data_loc, output_dir, level = parse_args()
    run_program(data_loc, output_dir, level, Database())  # 'D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz'


def run_program(data_loc: Path, output_dir: Path, level: CsoportType, db: Database) -> Path | None:
    try:
        # only add email address - name pairs, if names, or emails need to be fixed:
        collective_df, output_file_name = process(data_loc, db, level, output_dir)
        collective_df.reset_index(inplace=True)
        print(f"Saving report to {output_file_name}")
        to_excel(output_file_name, collective_df)
        print("Done. Bye! :)\n")
        return output_file_name
    except ReportError as e:
        print(e)
        return None


def parse_args() -> tuple[Path, Path, CsoportType]:
    parser = argparse.ArgumentParser(description="Jelenléti adatok feldolgozása és Excel export készítés")
    parser.add_argument(
        "folder",
        type=Path,
        help="Bemeneti mappa elérési útja. Pl.: 'D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz'",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports"),
        help=("Kimeneti mappa az összefoglaló Excel fájlhoz " "(alapértelmezett: ./reports)"),
    )

    parser.add_argument(
        "--szint",
        choices=["kezdo", "kozep", "halado", "egyeb"],
        default="kozep",
        help="Csoport szintje: kezdo | kozep | halado | egyeb (alapértelmezett: kozep)",
    )

    args = parser.parse_args()

    if not args.folder.exists():
        parser.error(f"A megadott útvonal nem létezik: {args.folder}")

    if not args.folder.is_dir():
        parser.error(f"A megadott útvonal nem mappa: {args.folder}")

    # kimeneti mappa létrehozása
    args.out.mkdir(parents=True, exist_ok=True)

    return args.folder, args.out, args.szint


if __name__ == "__main__":
    main()
