import re
import datetime
import locale

from collections import defaultdict
import pandas as pd
from pathlib import Path
import os
from typing import Literal

from jelenlet.errors import ReportError
from jelenlet.fixer import try_fix_name_issues, catch_email_typos, name_to_dummy_email
from jelenlet.database import Database

CsoportType = Literal["kezdo", "kozep", "halado", "egyeb"]

# Constants
EMAIL = "E-mail-cím"  # column names in the xlsx files
NAME = "Teljes név"
JOSSZ = "Jössz próbára?"


# Pattern for not the usual 3 group levels. Override before run with necessary pattern.
XLSX_FILENAME_DATA_CUSTOM_PATTERN = r".*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx"

XLSX_FILENAME_DATE_PATTERNS = {
    "kezdo": re.compile(r"Kezdős? próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx", re.IGNORECASE),
    "kozep": re.compile(r"Középhaladós? próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx", re.IGNORECASE),
    "halado": re.compile(r"Haladós? próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx", re.IGNORECASE),
    "egyeb": re.compile(XLSX_FILENAME_DATA_CUSTOM_PATTERN, re.IGNORECASE),
}
# Example file name: 'Középhaladós próba - 2024. 09. 09. (válaszok).xlsx'


def check__alternative_column_names(file_name: str, df: pd.DataFrame):
    EMAIL_ALTERNATIVES = ["Email Address", "Email", "E-mail", "e-mail:", "Email Address:", "Email:", "E-mail:", "e-mail:"]
    if EMAIL not in df.columns:
        for col in EMAIL_ALTERNATIVES:
            if col in df.columns:
                df[EMAIL] = df[col]
                break
    NAME_ALTERNATIVES = ["teljes név", "Name", "Full name", "Teljes név:", "Name:", "Full name:"]
    if NAME not in df.columns:
        for col in NAME_ALTERNATIVES:
            if col in df.columns:
                df[NAME] = df[col]
                break

    if EMAIL in df.columns and NAME in df.columns and sum(1 for c in df.columns if c == NAME) == 1:
        pass
    else:
        raise ReportError(
            f"{file_name} format was not proper. XLSX file needs 1 email column called '{EMAIL}', 1 name column called '{NAME}' only "
            + f"{df.columns}"
        )


def process(folder: Path, db: Database, level: CsoportType, output_dir: Path) -> tuple[pd.DataFrame, Path]:

    EMAIL_NAMES_DATABASE = db.read_email_name_database()

    def read_dataframes() -> tuple[list[pd.DataFrame], list[str]]:
        file_names: list[str] = [os.path.join(folder, f) for f in os.listdir(folder) if XLSX_FILENAME_DATE_PATTERNS[level].match(f)]
        print(f"Found {len(file_names)} files.")
        if not file_names:
            raise ReportError(f"Did not found xlsx files matching the pattern: {XLSX_FILENAME_DATE_PATTERNS[level]}")

        dfs = [pd.read_excel(f) for f in file_names]
        # strip empty spaces and check NaN emails
        for df, file_name in zip(dfs, file_names):
            check__alternative_column_names(file_name, df)
            df[EMAIL] = df[EMAIL].str.strip()
            df[NAME] = df[NAME].str.strip()
            # check for Nan names
            nan_mask = df[NAME].isna()
            if nan_mask.any():
                print(f"[WARNING] NaN - empty names found in file: {file_name}")
                df[NAME].fillna("ISMERETLEN", inplace=True)
            # check for NaN email addresses
            nan_mask = df[EMAIL].isna()
            if nan_mask.any():
                names_with_nan_email = df.loc[nan_mask, NAME].dropna().unique().tolist()
                print(f"[WARNING] NaN email address(es) found in file: {file_name} Names: {names_with_nan_email}")
            # fill NaN emails with generated dummy emails
            df.loc[nan_mask, EMAIL] = df.loc[nan_mask, NAME].apply(name_to_dummy_email)

            df[NAME] = df[EMAIL].map(EMAIL_NAMES_DATABASE).fillna(df[NAME])
        return dfs, file_names

    def build_journal(dataframes: list[pd.DataFrame]) -> defaultdict[str, list[str]]:
        email_names = defaultdict(list)
        for df in dataframes:
            for email, name in zip(df[EMAIL].to_numpy(), df[NAME].to_numpy()):
                # if name not in email_names[email]:
                email_names[email].append(name)
        return email_names

    def change_names_in_dataframes(email_name: dict[str, str], dfs: list[pd.DataFrame]):
        for df in dfs:
            df[NAME] = df[EMAIL].map(email_name).fillna(df[NAME])

    def change_emails_in_dataframes(wrong_right_emails, dfs):
        for df in dfs:
            df[EMAIL] = df[EMAIL].map(wrong_right_emails).fillna(df[EMAIL])

    def cleanup_dataframes(db: Database):
        dfs, file_names = read_dataframes()
        # try to catch name typos:
        email_names = build_journal(dfs)
        email_name = try_fix_name_issues(email_names, db)
        print("-------")
        change_names_in_dataframes(email_name, dfs)  # Use email_names dict to fill up dataframes
        # try to catch email typos
        wrong_right_emails, email_errors = catch_email_typos(email_name, db)
        if email_errors:
            raise ReportError("Errors found during email checks. Add apropriate lines to email_name_database to continue. Aborting...")
        change_emails_in_dataframes(wrong_right_emails, dfs)

        email_names_full = {k: v for k, v in email_name.items()}  # full and fixed email-name dictionary
        return dfs, file_names, email_names_full

    # r"D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz\Középhaladós próba - 2025. 09. 29. (válaszok).xlsx"
    def find_date(path: str) -> datetime.date:
        return find_date_by_pattern(path, XLSX_FILENAME_DATE_PATTERNS[level])

    def construct_collective_dataframe(file_names: list[str], dfs: list[pd.DataFrame], email_names_full: dict[str, str]):
        emails, names = list(zip(*email_names_full.items()))
        emails = list(emails)
        names = list(names)
        email_attendance_count = defaultdict(int)

        data: dict[str | datetime.date, list] = {"Név": names}
        data["Össz."] = [0 for _ in emails]  # add summary column before - to make this the 3rd column.

        pairs = sorted(zip(file_names, dfs), key=lambda p: find_date(p[0]))
        for file_name, df in pairs:
            event_date = find_date(file_name)
            if JOSSZ in df.columns:
                df = df[df[JOSSZ].str.lower() != "nem"]  # Filter out, "Jössz próbára?" -> Nem rows
            emails_of_attendees = set(df[EMAIL].to_numpy())
            data[event_date.strftime("%Y.%m.%d")] = ["X" if email in emails_of_attendees else "_" for email in emails]

            for email in emails_of_attendees:
                email_attendance_count[email] += 1

        data["Össz."] = [email_attendance_count[email] for email in emails]

        new_df = pd.DataFrame(data, index=emails)
        new_df.index.name = "Email"
        return new_df

    dfs, file_names, email_names_full = cleanup_dataframes(db)
    df_summary = construct_collective_dataframe(file_names, dfs, email_names_full)
    # trying to fix order problem with hungarian accented letters
    locale.setlocale(locale.LC_COLLATE, "hu_HU.UTF-8")
    # df_summary.sort_values(by=['Név'], inplace=True)
    df_summary.sort_values(by="Név", key=lambda s: s.map(locale.strxfrm), inplace=True)
    return df_summary, generate_output_filename(file_names, level, output_dir)


def generate_output_filename(file_names: list[str], level, dir: Path) -> Path:
    pat = XLSX_FILENAME_DATE_PATTERNS[level]
    dates_in_filenames = [find_date_by_pattern(p, pat) for p in file_names]
    first, last = date_to_str(min(dates_in_filenames)), date_to_str(max(dates_in_filenames))
    output_file_name = Path(dir).joinpath(f"{level}_proba_osszegzes_{first}-{last}_[{now_to_file_name_part()}].xlsx")
    return output_file_name


def date_to_str(d: datetime.date):
    return d.strftime("%Y_%m_%d")


def now_to_file_name_part():
    dt = datetime.datetime.now()
    date_part = dt.strftime("%Y_%m_%d__%H_%M")
    return date_part


def find_date_by_pattern(path: str, pattern) -> datetime.date:
    match = pattern.search(path)
    if match is None:
        raise ReportError(f"No date found in path: {path}")
    y, m, d = (int(x) for x in match.groups())
    return datetime.date(y, m, d)
