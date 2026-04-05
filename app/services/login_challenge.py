from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random
import secrets
from threading import Lock


@dataclass
class _Challenge:
    answer: int
    expires_at: datetime


_challenges: dict[str, _Challenge] = {}
_lock = Lock()
_ttl_seconds = 120


def _cleanup_expired() -> None:
    now = datetime.now(timezone.utc)
    expired = [key for key, item in _challenges.items() if item.expires_at <= now]
    for key in expired:
        _challenges.pop(key, None)


def generate_login_challenge() -> dict[str, str | int]:
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-", "*"])

    if op == "-":
        a, b = max(a, b), min(a, b)
        answer = a - b
    elif op == "*":
        answer = a * b
    else:
        answer = a + b

    question = f"Quanto é {a} {op} {b}?"
    challenge_id = secrets.token_urlsafe(12)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_ttl_seconds)

    with _lock:
        _cleanup_expired()
        _challenges[challenge_id] = _Challenge(answer=answer, expires_at=expires_at)

    return {
        "challenge_id": challenge_id,
        "question": question,
        "expires_in_seconds": _ttl_seconds,
    }


def verify_login_challenge(challenge_id: str, answer: str) -> bool:
    with _lock:
        _cleanup_expired()
        challenge = _challenges.pop(challenge_id, None)

    if not challenge:
        return False

    try:
        numeric_answer = int(str(answer).strip())
    except ValueError:
        return False

    return numeric_answer == challenge.answer
