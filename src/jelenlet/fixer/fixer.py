import re


def name_to_dummy_email(name: str) -> str:
    # fallback in case name itself is NaN or empty
    if not isinstance(name, str) or not name.strip():
        return "unknown@dummy.local"

    # normalize name -> lowercase, ascii-ish, dot-separated
    local_part = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    return f"{local_part}@DUMMY.LOCAL"
