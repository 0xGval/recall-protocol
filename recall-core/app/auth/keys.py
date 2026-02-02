import hashlib
import secrets


def generate_api_key() -> str:
    return "recall_" + secrets.token_hex(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
