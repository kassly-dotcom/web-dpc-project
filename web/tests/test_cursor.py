"""О1.5. Чисті тести курсора — без бази."""

import base64
from datetime import datetime, timezone

import pytest

from web.backend.cursor import InvalidCursor, decode_cursor, encode_cursor

T = datetime(2026, 11, 18, 18, 5, tzinfo=timezone.utc)


def test_roundtrip_keeps_time_and_id():
    t, i = decode_cursor(encode_cursor(T, "0b6f6a52-5f1e-4c4a-9a51-1d7d2d3f8e10"))
    assert t == T
    assert i == "0b6f6a52-5f1e-4c4a-9a51-1d7d2d3f8e10"


def test_cursor_is_url_safe_and_opaque():
    c = encode_cursor(T, "r43")
    assert "=" not in c and "+" not in c and "/" not in c


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.mark.parametrize(
    "bad",
    [
        "not-base64!!!",
        "abc",
        _b64(b"not json"),
        _b64(b"[1,2]"),
        _b64(b'{"t":"2026-11-18T18:05:00Z"}'),
        _b64(b'{"t":"2026-11-18T18:05:00Z","i":"x","extra":1}'),
        _b64(b'{"t":"yesterday","i":"x"}'),
        _b64(b'{"t":"2026-11-18T18:05:00","i":"x"}'),  # без часової зони
        _b64(b'{"t":"2026-11-18T18:05:00Z","i":""}'),
        _b64(b'{"t":"2026-11-18T18:05:00Z","i":5}'),
    ],
)
def test_corrupted_cursor_is_rejected(bad):
    with pytest.raises(InvalidCursor):
        decode_cursor(bad)
