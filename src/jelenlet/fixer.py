import csv
import string
from functools import cache
from jelenlet.paths import POSSIBLE_NAMES_CSV

from jelenlet.errors import ReportError
from jelenlet.database import read_email_name_database, db_append

EMAIL_NAMES_DATABASE = read_email_name_database()


class Fixer:
    def __init__(self) -> None:
        pass


@cache
def read_allowed_names() -> set[str]:
    with open(POSSIBLE_NAMES_CSV, encoding="utf-8") as csvfile:
        rows = csv.reader(csvfile, delimiter=";")
        next(rows)  # skip header
        names = {r[0] for r in rows}
        if not names:
            raise ReportError("Allowed names were not found in CSV!")
        return names


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
        print("\tIf incorrect, add either of following lines to EMAIL_NAME_DATABASE")
        for n in names:
            print(f"\t{email} = {n}")
        return result

    print(f"ACTION REQUIRED: Could not autofix names: {names}")
    print("\tAdd either of following lines to EMAIL_NAME_DATABASE dictionary:")
    db_append("\n# Uncomment one of these:")
    for n in names:
        print(f"\t\t{email} = {n}")
        db_append(f"# {email} = {n}")
    return names
