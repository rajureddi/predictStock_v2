"""One account. No registration. The password is checked on the server."""
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COOKIE = "qt_session"
MAX_AGE = 14 * 24 * 3600
DEFAULT_USERNAME = "quant"
DEFAULT_PASSWORD = "MapleSnow#92"
_FAILS: list[float] = []


def auth_enabled() -> bool:
    return os.environ.get("MARKETMIND_AUTH", "1") != "0"


def auth_path() -> Path:
    override = os.environ.get("MARKETMIND_AUTH_FILE")
    return Path(override) if override else ROOT / "data" / "auth.json"


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def load_account() -> dict:
    path = auth_path()
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    salt = secrets.token_hex(16)
    doc = {
        "username": DEFAULT_USERNAME,
        "salt": salt,
        "password_hash": _hash(DEFAULT_PASSWORD, salt),
        "secret": secrets.token_hex(32),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return doc


def too_many_attempts() -> bool:
    now = time.time()
    _FAILS[:] = [t for t in _FAILS if now - t < 600]
    return len(_FAILS) >= 8


def note_failure() -> None:
    _FAILS.append(time.time())


def verify(username: str, password: str) -> bool:
    doc = load_account()
    user_ok = hmac.compare_digest((username or "").strip(), doc["username"])
    digest = _hash(password or "", doc["salt"])
    pass_ok = hmac.compare_digest(digest, doc["password_hash"])
    return user_ok and pass_ok


def make_token() -> str:
    doc = load_account()
    exp = int(time.time()) + MAX_AGE
    payload = f"{doc['username']}.{exp}.{secrets.token_hex(8)}"
    sig = hmac.new(doc["secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_token(token: str) -> bool:
    parts = (token or "").split(".")
    if len(parts) != 4:
        return False
    user, exp, nonce, sig = parts
    doc = load_account()
    payload = f"{user}.{exp}.{nonce}"
    expected = hmac.new(doc["secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    if not hmac.compare_digest(user, doc["username"]):
        return False
    try:
        return int(exp) >= time.time()
    except ValueError:
        return False
