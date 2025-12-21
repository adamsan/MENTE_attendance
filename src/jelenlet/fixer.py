import csv
import string
from functools import cache
from collections import defaultdict

from jelenlet.paths import POSSIBLE_NAMES_CSV
from jelenlet.errors import ReportError
from jelenlet.database import db_append

@cache
def read_allowed_names() -> set[str]:
    with open(POSSIBLE_NAMES_CSV, encoding="utf-8") as csvfile:
        rows = csv.reader(csvfile, delimiter=";")
        next(rows)  # skip header
        names = {r[0] for r in rows}
        if not names:
            raise ReportError("Allowed names were not found in CSV!")
        return names


def fix_name(names, email, EMAIL_NAMES_DATABASE) -> list[str]:
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


def can_fix_names(email_names, EMAIL_NAMES_DATABASE) -> bool:
    # If one email address has multiple names -> problem: capitalization, accented letters, typos, different name variations
    fixed = {}
    for email, names in email_names.items():
        if len(names) > 1:
            fixed[email] = fix_name(names, email, EMAIL_NAMES_DATABASE)
    email_names.update(fixed)

    if any(len(names) > 1 for _, names in email_names.items()):
        print("Manual adjustment needed for EMAIL_NAME_DATABASE")
        return True
    return False


def catch_email_typos(email_names, EMAIL_NAMES_DATABASE) -> dict[str, str]:
    name_emails = defaultdict(list)
    wrong_right_emails = {}
    for e, ns in email_names.items():
        name_emails[ns[0]].append(e)

    for name, emails in name_emails.items():
        if len(emails) > 1:
            if all(e not in EMAIL_NAMES_DATABASE for e in emails):
                print(f"Problem found:'{name}' has multiple email addresses: {emails}")
                print("\tAdd either of following lines to EMAIL_NAME_DATABASE:")
                db_append("\n# Uncomment (at least) one of these lines:")
                for e in emails:
                    print(f"{e} = {name}")
                    db_append(f"# {e} = {name}")
            else:  # email-name is already in EMAIL_NAME_DATABASE dict
                valid_emails = [e for e in emails if e in EMAIL_NAMES_DATABASE]
                if len(valid_emails) == 1:
                    valid_email = valid_emails[0]
                    wrong_emails = {e for e in emails if e != valid_email}
                    for w in wrong_emails:
                        wrong_right_emails[w] = valid_email
                        del email_names[w]  # modify email_names - remove wrong email address
                elif len(valid_emails) > 1:
                    # handle, if we have two person with the same name / different email TODO: Do I need to do anything here?
                    print(f"Looks like different persons with the same name... {name} {valid_emails}")

    return wrong_right_emails
