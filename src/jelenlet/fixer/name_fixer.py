import csv
import string
from functools import cache
from collections import Counter
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
    if most[1] >= 2 and most[1] > confidence_factor * rest_occurance:
        return NameIssue(email, list(set(names)), most[0], f"based on occurance {most[1]} to {rest_occurance}")
    return None


def detect_issue(email: str, names: list[str]) -> NameIssue | None:
    if len(set(names)) == 1:
        return None
    resolvers = [resolve_capitulization, resolve_only_one_allowed_christian_name, resolve_by_majority]
    for resolver in resolvers:
        issue = resolver(email, names)
        if issue:
            return issue
    return NameIssue(email, list(set(names)), None, "ACTION REQUIRED: Could not make suggestion")


def find_name_issues(email_names: dict[str, list[str]], EMAIL_NAMES_DB: dict[str, str]) -> list[NameIssue]:
    issues = (detect_issue(e, ns) for e, ns in email_names.items() if e not in EMAIL_NAMES_DB)
    return [i for i in issues if i]


def write_name_issues_to_db(issues: list[NameIssue], db: Database):
    for issue in issues:
        for line in issue.lines():
            db.db_append(line)


def try_fix_name_issues(email_names: dict[str, list[str]], db: Database) -> dict[str, str]:
    name_issues = find_name_issues(email_names, db.read_email_name_database())
    if name_issues:
        write_name_issues_to_db(name_issues, db)
        raise ReportError("Errors found during name checks. Add apropriate lines to EMAIL_NAME_DATABASE to continue. Aborting...")

    DB = db.read_email_name_database()
    new_email_name = {}
    for email in email_names:
        new_email_name[email] = DB[email] if email in DB else email_names[email][0]
    return new_email_name
