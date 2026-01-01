from collections import defaultdict, Counter
from dataclasses import dataclass

from jelenlet.errors import ReportError
from jelenlet.database import Database


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
    if most[1] >= 2 and most[1] > confidence_factor * rest_occurance:
        return EmailIssue(name, list(set(emails)), most[0], f"based on occurance {most[1]} to {rest_occurance}")
    return None


def detect_issue_email(name: str, emails: list[str]) -> EmailIssue | None:
    if len(set(emails)) == 1:
        return None
    resolvers = [resolve_email_gmail_typo, resolve_email_by_majority]
    for resolver in resolvers:
        issue = resolver(name, emails)
        if issue:
            return issue
    return EmailIssue(name, list(set(emails)), None, "ACTION REQUIRED: Could not make suggestion")


def find_email_issues(name_emails: dict[str, list[str]], email_name_db: dict[str, str]):
    issues = (detect_issue_email(n, es) for n, es in name_emails.items() if n not in email_name_db.values())
    return [i for i in issues if i]


def write_email_issues_to_db(issues: list[EmailIssue], db: Database):
    for i in issues:
        for line in i.lines():
            db.db_append(line)


def try_fix_email_issues(
    email_names: dict[str, list[str]], email_name: dict[str, str], db: Database
) -> tuple[dict[str, str], dict[str, str]]:
    EMAIL_NAMES_DATABASE = db.read_email_name_database()

    name_emails = defaultdict(list)
    for e, ns in email_names.items():
        for n in ns:
            name_emails[n].append(e)

    email_issues = find_email_issues(name_emails, EMAIL_NAMES_DATABASE)
    if email_issues:
        write_email_issues_to_db(email_issues, db)
        raise ReportError("Errors found during email checks. Add apropriate lines to email_name_database to continue. Aborting...")

    wrong_right_emails = {}
    for name, emails in name_emails.items():
        emails = list(set(emails))
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
