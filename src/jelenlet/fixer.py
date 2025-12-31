import csv
import re
import string
from functools import cache
from collections import defaultdict, Counter
from dataclasses import dataclass

from jelenlet.paths import POSSIBLE_NAMES_CSV
from jelenlet.errors import ReportError
from jelenlet.database import Database


@cache
def read_allowed_names() -> set[str]:
    with open(POSSIBLE_NAMES_CSV, encoding="utf-8") as csvfile:
        rows = csv.reader(csvfile, delimiter=";")
        next(rows)  # skip header
        names = {r[0] for r in rows}
        if not names:
            raise ReportError("Allowed names were not found in CSV!")
        return names


@dataclass
class NameIssue:
    email: str
    names: list[str]
    suggestion: str | None
    reason: str

    def lines(self):
        if self.suggestion:
            result = [f"\n# Resolving with: [{self.suggestion}] reason:[{self.reason}]", f"{self.email} = {self.suggestion}"]
        else:
            result = [f"\n# Uncomment one of these. reason[{self.reason}]"]
        for n in set(self.names):
            if n != self.suggestion:
                result.append(f"# {self.email} = {n}")
        return result


def resolve_capitulization(email: str, names: list[str]) -> NameIssue | None:
    lowercase_names_set = {n.lower() for n in names}
    if len(lowercase_names_set) == 1:
        suggestion = string.capwords(names[0])
        return NameIssue(email, list(set(names)), suggestion, "simple uppercase - lowercase problem detected")
    return None


def resolve_only_one_allowed_christian_name(email: str, names: list[str]) -> NameIssue | None:
    names_unique = list(set(names))
    # v[i] = True, if names_unique[i]'s last part is an allowed christian name
    v: list[bool] = [n.split()[-1] in read_allowed_names() for n in names_unique]
    if sum(1 if x else 0 for x in v) == 1:  # if there is only one such name variation, that has a valid first name
        suggestion = names_unique[v.index(True)]
        return NameIssue(email, list(set(names)), suggestion, "only one last christian name detected")
    return None


def resolve_by_majority(email: str, names: list[str]) -> NameIssue | None:
    occurances = Counter(names).most_common()
    most = occurances.pop(0)
    rest_occurance = sum(o[1] for o in occurances)
    confidence_factor = 1
    if most[1] > confidence_factor * rest_occurance:
        return NameIssue(email, list(set(names)), most[0], f"based on occurance {most[1]} to {rest_occurance}")
    return None


def detect_issue(email: str, names: list[str]) -> NameIssue | None:
    if len(names) == 0:  # Question: is this even necessary, did we already fill empty names?
        return NameIssue(email, [], email, f"Missing name for email: {email}")
    if len(set(names)) == 1:
        return None
    resolvers = [resolve_capitulization, resolve_only_one_allowed_christian_name, resolve_by_majority]
    for resolver in resolvers:
        issue = resolver(email, names)
        if issue:
            return issue
    return NameIssue(email, list(set(names)), None, "ACTION REQUIRED: Could not make suggestion")


def find_name_issues(email_names: dict[str, list[str]], db: Database) -> list[NameIssue]:
    EMAIL_NAME_DB = db.read_email_name_database()
    issues = (detect_issue(e, ns) for e, ns in email_names.items() if e not in EMAIL_NAME_DB)
    return [i for i in issues if i]


def write_name_issues_to_db(issues: list[NameIssue], db: Database):
    for issue in issues:
        for line in issue.lines():
            db.db_append(line)


def try_fix_name_issues(email_names: dict[str, list[str]], db: Database) -> dict[str, str]:
    name_issues = find_name_issues(email_names, db)
    if name_issues:
        write_name_issues_to_db(name_issues, db)
        raise ReportError("Errors found during name checks. Add apropriate lines to EMAIL_NAME_DATABASE to continue. Aborting...")

    DB = db.read_email_name_database()
    new_email_name = {}
    for email in email_names:
        new_email_name[email] = DB[email] if email in DB else email_names[email][0]
    return new_email_name


@dataclass
class EmailIssue:
    name: str
    emails: list[str]
    suggestion: str | None
    reason: str

    def lines(self):
        if self.suggestion:
            result = [f"\n# Resolving with: [{self.suggestion}] reason:[{self.reason}]", f"{self.suggestion} = {self.name}"]
        else:
            result = ["\n# Uncomment (at least) one of these:"]
        for e in set(self.emails):
            if e != self.suggestion:
                result.append(f"# {e} = {self.name}")
        return result


def resolve_email_gmail_typo(name, emails) -> EmailIssue | None:
    emails = list(set(emails))
    usernames = set(e.split("@")[0] for e in emails if "@" in e)
    domains = set(e.split("@")[1] for e in emails if "@" in e)
    all_same_username = len(usernames) == 1
    if all_same_username and len(domains) >= 2 and "gmail.com" in domains:
        suggestion = [e for e in emails if e.lower().endswith("@gmail.com")][0]
        return EmailIssue(name, emails, suggestion, "probably mistyped @gmail address")
    return None


def resolve_email_by_majority(name, emails) -> EmailIssue | None:
    occurances = Counter(emails).most_common()
    most = occurances.pop(0)
    rest_occurance = sum(o[1] for o in occurances)
    confidence_factor = 1
    if most[1] > confidence_factor * rest_occurance:
        return EmailIssue(name, list(set(emails)), most[0], f"based on occurance {most[1]} to {rest_occurance}")
    return None


def detect_issue_email(name: str, emails: list[str]) -> EmailIssue | None:
    if len(emails) == 1:
        return None
    resolvers = [resolve_email_gmail_typo, resolve_email_by_majority]
    for resolver in resolvers:
        issue = resolver(name, emails)
        if issue:
            return issue
    return EmailIssue(name, list(set(emails)), None, "ACTION REQUIRED: Could not make suggestion")


def find_email_issues(name_emails: dict[str, list[str]], db: dict[str, str]):
    issues = (detect_issue_email(n, es) for n, es in name_emails.items() if n not in db.values())
    return [i for i in issues if i]


def write_email_issues_to_db(issues: list[EmailIssue], db: Database):
    for i in issues:
        for line in i.lines():
            db.db_append(line)


def try_fix_email_issues(email_name: dict[str, str], db: Database) -> tuple[dict[str, str], dict[str, str]]:
    EMAIL_NAMES_DATABASE = db.read_email_name_database()
    name_emails = defaultdict(list)
    for e, n in email_name.items():
        name_emails[n].append(e)

    email_issues = find_email_issues(name_emails, EMAIL_NAMES_DATABASE)
    if email_issues:
        write_email_issues_to_db(email_issues, db)
        raise ReportError("Errors found during email checks. Add apropriate lines to email_name_database to continue. Aborting...")

    wrong_right_emails = {}
    for name, emails in name_emails.items():
        if len(emails) > 1:
            valid_emails = [e for e in emails if e in EMAIL_NAMES_DATABASE]
            if len(valid_emails) == 1:
                valid_email = valid_emails[0]
                wrong_emails = {e for e in emails if e != valid_email}
                for w in wrong_emails:
                    wrong_right_emails[w] = valid_email
            else:  # more valid emails:
                # handle, if we have two person with the same name / different email TODO: Do I need to do anything here?
                print(f"Looks like different persons with the same name... {name} {valid_emails}")

    email_name_without_wrong = {e: n for e, n in email_name.items() if e not in wrong_right_emails}
    print(f"Wrong->Right email substitutions:{wrong_right_emails}")
    return wrong_right_emails, email_name_without_wrong


def name_to_dummy_email(name: str) -> str:
    # fallback in case name itself is NaN or empty
    if not isinstance(name, str) or not name.strip():
        return "unknown@dummy.local"

    # normalize name -> lowercase, ascii-ish, dot-separated
    local_part = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    return f"{local_part}@DUMMY.LOCAL"
