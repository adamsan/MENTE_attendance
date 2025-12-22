import re
import datetime
import locale

from collections import defaultdict
import pandas as pd
from pathlib import Path
import os

from jelenlet.errors import ReportError
from jelenlet.fixer import can_fix_names, catch_email_typos, name_to_dummy_email

# Constants
EMAIL = "E-mail-cím"  # column names in the xlsx files
NAME = "Teljes név"


# Pattern for not the usual 3 group levels. Override before run with necessary pattern.
XLSX_FILENAME_DATA_CUSTOM_PATTERN = r"Egyéb próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx"

XLSX_FILENAME_DATE_PATTERNS = {
    "kezdo": re.compile(r"Kezdős? próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx", re.IGNORECASE),
    "kozep": re.compile(r"Középhaladós? próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx", re.IGNORECASE),
    "halado": re.compile(r"Haladós? próba.*(\d{4})\. ?(\d{1,2})\. ?(\d{1,2})\..*\.xlsx", re.IGNORECASE),
    "egyeb": re.compile(XLSX_FILENAME_DATA_CUSTOM_PATTERN, re.IGNORECASE),
}
# Example file name: 'Középhaladós próba - 2024. 09. 09. (válaszok).xlsx'


def process(folder: Path, EMAIL_NAMES_DATABASE, level) -> pd.DataFrame:
    def read_dataframes() -> tuple[list[pd.DataFrame], list[str]]:
        file_names: list[str] = [os.path.join(folder, f) for f in os.listdir(folder) if XLSX_FILENAME_DATE_PATTERNS[level].match(f)]
        print(f"Found {len(file_names)} files.")
        if not file_names:
            raise ReportError(f"Did not found xlsx files matching the pattern: {XLSX_FILENAME_DATE_PATTERNS[level]}")

        dfs = [pd.read_excel(f) for f in file_names]
        # strip empty spaces and check NaN emails
        for df, file_name in zip(dfs, file_names):
            df[EMAIL] = df[EMAIL].str.strip()
            df[NAME] = df[NAME].str.strip()
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
                if name not in email_names[email]:
                    email_names[email].append(name)
        return email_names

    def change_names_in_dataframes(email_names, dfs):
        email_names_db = {k: v[0] for k, v in email_names.items()}
        for df in dfs:
            df[NAME] = df[EMAIL].map(email_names_db).fillna(df[NAME])

    def change_emails_in_dataframes(wrong_right_emails, dfs):
        for df in dfs:
            df[EMAIL] = df[EMAIL].map(wrong_right_emails).fillna(df[EMAIL])

    def cleanup_dataframes(EMAIL_NAMES_DATABASE):
        dfs, file_names = read_dataframes()
        # try to catch name typos:
        email_names = build_journal(dfs)
        if can_fix_names(email_names, EMAIL_NAMES_DATABASE):
            raise ReportError("Errors found during name checks. Add apropriate lines to EMAIL_NAME_DATABASE to continue. Aborting...")
        print("-------")
        change_names_in_dataframes(email_names, dfs)  # Use email_names dict to fill up dataframes
        # try to catch email typos
        wrong_right_emails, email_errors = catch_email_typos(email_names, EMAIL_NAMES_DATABASE)
        if email_errors:
            raise ReportError("Errors found during email checks. Add apropriate lines to email_name_database to continue. Aborting...")
        change_emails_in_dataframes(wrong_right_emails, dfs)

        email_names_full = {k: v[0] for k, v in email_names.items()}  # full and fixed email-name dictionary
        return dfs, file_names, email_names_full

    # r"D:/workspaces/jupyter_notebooks/kozephalados_jelenleti/data/2025_26_osz\Középhaladós próba - 2025. 09. 29. (válaszok).xlsx"
    def find_date(file_path):
        match = XLSX_FILENAME_DATE_PATTERNS[level].search(file_path)
        if match is None:
            raise ReportError(f"No date found in path: {file_path}")
        y, m, d = (int(x) for x in match.groups())
        return datetime.date(y, m, d)

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
            emails_of_attendees = set(df[EMAIL].to_numpy())
            data[event_date] = ["X" if email in emails_of_attendees else "_" for email in emails]

            for email in emails_of_attendees:
                email_attendance_count[email] += 1

        data["Össz."] = [email_attendance_count[email] for email in emails]

        new_df = pd.DataFrame(data, index=emails)
        new_df.index.name = "Email"
        return new_df

    dfs, file_names, email_names_full = cleanup_dataframes(EMAIL_NAMES_DATABASE)
    df_summary = construct_collective_dataframe(file_names, dfs, email_names_full)
    # trying to fix order problem with hungarian accented letters
    locale.setlocale(locale.LC_COLLATE, "hu_HU.UTF-8")
    # df_summary.sort_values(by=['Név'], inplace=True)
    df_summary.sort_values(by="Név", key=lambda s: s.map(locale.strxfrm), inplace=True)
    return df_summary
