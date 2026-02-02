import secrets
import string

_ALPHABET = string.ascii_uppercase + string.digits


def generate_short_id() -> str:
    code = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"RCL-{code}"
