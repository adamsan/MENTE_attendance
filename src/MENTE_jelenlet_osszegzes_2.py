import re
import datetime
import locale
import string
import csv
from collections import defaultdict
import pandas as pd
from pathlib import Path
import os
import argparse
from functools import cache
from MENTE_jelenlet_config import EMAIL_NAMES_DATABASE

# Constants
EMAIL = "E-mail-cím"  # column names in the xlsx file
NAME = "Teljes név"
XLSX_FILENAME_DATE_PATTERN = re.compile(r"Középhaladós próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx")
# Example file name: 'Középhaladós próba - 2024. 09. 09. (válaszok).xlsx'

# expects: a csv file, ';' separated, first column is names, first row is header row
POSSIBLE_NAMES_CSV = "D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/anyakonyvezheto_utonevek_2019_08.csv"


def process(folder: Path) -> pd.DataFrame:
    def read_dataframes() -> tuple[list[pd.DataFrame], list[str]]:
        file_names: list[str] = [os.path.join(folder, f) for f in os.listdir(folder) if XLSX_FILENAME_DATE_PATTERN.match(f)]
        dfs = [pd.read_excel(f) for f in file_names]
        # strip empty spaces
        for df in dfs:
            df[EMAIL] = df[EMAIL].str.strip()
            df[NAME] = df[NAME].str.strip()
            df[NAME] = df[EMAIL].map(EMAIL_NAMES_DATABASE).fillna(df[NAME])
        return dfs, file_names

    def build_journal(dataframes: list[pd.DataFrame]) -> defaultdict[str, list[str]]:
        email_names = defaultdict(list)
        for df in dataframes:
            for email, name in zip(df[EMAIL].to_numpy(), df[NAME].to_numpy()):
                if name not in email_names[email]:
                    email_names[email].append(name)
        return email_names

    @cache
    def read_allowed_names() -> set[str]:
        with open(POSSIBLE_NAMES_CSV, encoding="utf-8") as csvfile:
            rows = csv.reader(csvfile, delimiter=";")
            next(rows)  # skip header
            return {r[0] for r in rows}

    def fix_name(names, email) -> list[str]:
        print(f"Attempting to fix names: {names}")
        # check in database:
        if email and email in EMAIL_NAMES_DATABASE:
            result = [EMAIL_NAMES_DATABASE[email]]
            print(f"\tResolving with: {result} reason:[email found in db]")
            return result
        # check for capitalization
        lowercase_names_set = {n.lower() for n in names}
        if len(lowercase_names_set) == 1:
            result = [string.capwords(names[0])]
            print(f"\tResolving with:{result} [reason: uppercase - lowercase problem detected]")
            return [string.capwords(names[0])]

        # last name is a valid first name in hungarian
        v = [n.split()[-1] in read_allowed_names() for n in names]
        if sum(1 if x else 0 for x in v) == 1:  # if there is only one such name variation, that has a valid first name
            result = [names[v.index(True)]]
            print(f"\tResolving with: {result} reason:[only one last christian name detected]")
            print("\tIf incorrect, add either of following lines to EMAIL_NAME_DATABASE dictionary:")
            for n in names:
                print(f"\t\t'{email}':'{n}',")
            return result

        print(f"ACTION REQUIRED: Could not autofix names: {names}")
        print("\tAdd either of following lines to EMAIL_NAME_DATABASE dictionary:")
        for n in names:
            print(f"\t\t'{email}':'{n}',")
        return names

    def try_to_fix_name_problems(email_names) -> None:
        # If one email address has multiple names -> problem: capitalization, accented letters, typos, different name variations
        fixed = {}
        for email, names in email_names.items():
            if len(names) > 1:
                fixed[email] = fix_name(names, email)
        email_names.update(fixed)

    def are_nameproblems_still(email_names) -> bool:
        if any(len(names) > 1 for _, names in email_names.items()):
            print("Manual adjustment needed for EMAIL_NAME_DATABASE")
            return True
        return False

    def change_names_in_dataframes(email_names, dfs):
        email_names_db = {k: v[0] for k, v in email_names.items()}
        for df in dfs:
            df[NAME] = df[EMAIL].map(email_names_db).fillna(df[NAME])

    def catch_email_typos(email_names, dfs):
        name_emails = defaultdict(list)
        wrong_right_emails = {}
        for e, ns in email_names.items():
            name_emails[ns[0]].append(e)

        erros_found = False
        for name, emails in name_emails.items():
            if len(emails) > 1:
                if all(e not in EMAIL_NAMES_DATABASE for e in emails):
                    print(f"Problem found:'{name}' has multiple email addresses: {emails}")
                    print("\tAdd either of following lines to EMAIL_NAME_DATABASE dictionary:")
                    for e in emails:
                        print(f"\t\t'{e}':'{name}',")
                    erros_found = True
                else:  # email-name is already in EMAIL_NAME_DATABASE dict
                    valid_emails = [e for e in emails if e in EMAIL_NAMES_DATABASE][0]
                    if len(valid_emails) == 1:
                        valid_email = valid_emails[0]
                        wrong_emails = {e for e in emails if e != valid_email}
                        for w in wrong_emails:
                            wrong_right_emails[w] = valid_email
                            del email_names[w]  # modify email_names - remove wrong email address
                    elif len(valid_emails) > 1:
                        # handle, if we have two person with the same name / different email TODO: Do I need to do anything here?
                        print(f"Looks like different persons with the same name... {name} {valid_emails}")

        print("wrong->right")
        print(wrong_right_emails)
        # make changes in dataframes:
        for df in dfs:
            df[EMAIL] = df[EMAIL].map(wrong_right_emails).fillna(df[EMAIL])
        return erros_found

    def cleanup_dataframes():
        dfs, file_names = read_dataframes()
        # try to catch name typos:
        email_names = build_journal(dfs)
        try_to_fix_name_problems(email_names)
        print("-------")
        if are_nameproblems_still(email_names):
            raise RuntimeError("Errors found during name checks. Add apropriate lines to EMAIL_NAME_DATABASE to continue. Aborting...")
        change_names_in_dataframes(email_names, dfs)  # Use email_names dict to fill up dataframes
        # try to catch email typos
        if catch_email_typos(email_names, dfs):
            raise RuntimeError("Errors found during email checks. Add apropriate lines to email_name_database to continue. Aborting...")

        email_names_full = {k: v[0] for k, v in email_names.items()}  # full and fixed email-name dictionary
        return dfs, file_names, email_names_full

    # r"D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz\Középhaladós próba - 2025. 09. 29. (válaszok).xlsx"
    def find_date(file_path):
        match = XLSX_FILENAME_DATE_PATTERN.search(file_path)
        if match is None:
            raise ValueError(f"No date found in path: {file_path}")
        y, m, d = (int(x) for x in match.groups())
        return datetime.date(y, m, d)

    def construct_collective_dataframe(file_names: list[str], dfs: list[pd.DataFrame], email_names_full: dict[str, str]):
        emails, names = list(zip(*email_names_full.items()))
        emails = list(emails)
        names = list(names)
        print("construct_collective_dataframe called")
        email_attendance_count = defaultdict(int)

        data: dict[str | datetime.date, list] = {"Név": names}
        data["Össz."] = [0 for _ in emails]  # add summary column before - to make this the 3rd column.

        pairs = sorted(zip(file_names, dfs), key=lambda p: find_date(p[0]))
        for file_name, df in pairs:
            event_date = find_date(file_name)
            emails_of_attendees = set(df[EMAIL].to_numpy())
            data[event_date] = ["X" if email in emails_of_attendees else "_" for email in emails]

            for email in emails_of_attendees:
                email_attendance_count[email] += 1

        data["Össz."] = [email_attendance_count[email] for email in emails]

        new_df = pd.DataFrame(data, index=emails)
        new_df.index.name = "Email"
        return new_df

    dfs, file_names, email_names_full = cleanup_dataframes()
    print("Dataframes are clear now, continue processing them")
    df_summary = construct_collective_dataframe(file_names, dfs, email_names_full)
    # trying to fix order problem with hungarian accented letters
    locale.setlocale(locale.LC_COLLATE, "hu_HU.UTF-8")
    # df_summary.sort_values(by=['Név'], inplace=True)
    df_summary.sort_values(by="Név", key=lambda s: s.map(locale.strxfrm), inplace=True)
    return df_summary


def to_excel(fname, df):
    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)

        worksheet = writer.sheets["Sheet1"]

        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
            col_idx = df.columns.get_loc(column)
            worksheet.set_column(col_idx, col_idx, column_length)

        worksheet.freeze_panes(0, 3)


def main(data_loc: Path, output_dir: Path):
    # only add email address - name pairs, if names, or emails need to be fixed:
    collective_df = process(data_loc)
    collective_df.reset_index(inplace=True)
    output_file_name = output_dir.joinpath(f"kozephalado_proba_osszegzes_{Path(data_loc).name}.xlsx")
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
    main(folder, output_dir)  # 'D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz'
