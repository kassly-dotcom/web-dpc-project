"""О1.5. Непрозорий курсор для списку циклів.

Курсор — base64url від JSON {"t": created_at, "i": id} ОСТАННЬОГО показаного рядка.
Для клієнта це просто рядок: він передає його назад і не розбирає.
Обидва поля потрібні: за однакового created_at лише id дає однозначне продовження.
"""

import base64
import binascii
import json
from datetime import datetime, timezone


class InvalidCursor(ValueError):
    pass


def encode_cursor(created_at: datetime, row_id) -> str:
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    payload = {
        "t": created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "i": str(row_id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise InvalidCursor("cursor is not valid base64 JSON") from exc
    if not isinstance(data, dict) or set(data) != {"t", "i"}:
        raise InvalidCursor("cursor has unexpected structure")
    t, i = data["t"], data["i"]
    if not isinstance(t, str) or not isinstance(i, str) or not i or len(i) > 64:
        raise InvalidCursor("cursor fields have wrong types")
    try:
        created_at = datetime.fromisoformat(t)
    except ValueError as exc:
        raise InvalidCursor("cursor time is not ISO 8601") from exc
    if created_at.tzinfo is None:
        raise InvalidCursor("cursor time has no timezone")
    return created_at, i
