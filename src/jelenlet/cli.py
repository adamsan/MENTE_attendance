from pathlib import Path
import argparse

from jelenlet.process import process
from jelenlet.excel_export import to_excel
from jelenlet.process import REPORT_PREFIX
from jelenlet.errors import ReportError


def main(data_loc: Path, output_dir: Path):
    # only add email address - name pairs, if names, or emails need to be fixed:
    collective_df = process(data_loc)
    collective_df.reset_index(inplace=True)
    output_file_name = output_dir.joinpath(f"{REPORT_PREFIX}_osszegzes_{Path(data_loc).name}.xlsx")
    print(f"Saving report to {output_file_name}")
    to_excel(output_file_name, collective_df)
    print("Done. Bye! :)\n")


if __name__ == "__main__":

    def parse_args() -> tuple[Path, Path]:
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
        args = parser.parse_args()

        if not args.folder.exists():
            parser.error(f"A megadott útvonal nem létezik: {args.folder}")

        if not args.folder.is_dir():
            parser.error(f"A megadott útvonal nem mappa: {args.folder}")

        # kimeneti mappa létrehozása
        args.out.mkdir(parents=True, exist_ok=True)

        return args.folder, args.out

    folder, output_dir = parse_args()
    try:
        main(folder, output_dir)  # 'D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz'
    except ReportError as e:
        print(e)
