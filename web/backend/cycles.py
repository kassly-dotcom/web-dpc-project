"""О1.5. GET /v1/cycles — список циклів поточного користувача з курсорною пагінацією.

Порядок повний: created_at DESC, id DESC. Наступна сторінка — рядки строго ПІСЛЯ
пари (created_at, id) з курсора (порівняння пар у SQL). Вибираємо limit + 1 рядків:
зайвий лише показує, що є наступна сторінка; курсор будуємо за ОСТАННІМ ПОВЕРНЕНИМ.
Індекс під цей запит: (user_id, created_at DESC, id DESC) — міграція 003_cycle_list_index.sql.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection
from sqlalchemy.exc import DataError

from .auth import current_user_id
from .cursor import InvalidCursor, decode_cursor, encode_cursor
from .db import get_connection
from .problems import ProblemError

router = APIRouter(prefix="/v1/cycles", tags=["cycles"])

MAX_LIMIT = 50
DEFAULT_LIMIT = 20

_COLUMNS = """id, machine_id, program, duration_min, status, version, price_kopecks,
              created_at, expires_at, started_at, finished_at"""

FIRST_PAGE_SQL = f"""
    SELECT {_COLUMNS}
    FROM cycle
    WHERE user_id = %(user_id)s
    ORDER BY created_at DESC, id DESC
    LIMIT %(fetch)s
"""

NEXT_PAGE_SQL = f"""
    SELECT {_COLUMNS}
    FROM cycle
    WHERE user_id = %(user_id)s
      AND (created_at, id) < (%(after_t)s, %(after_id)s)
    ORDER BY created_at DESC, id DESC
    LIMIT %(fetch)s
"""


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _cycle_json(row) -> dict:
    return {
        "id": str(row.id),
        "machine_id": str(row.machine_id),
        "program": row.program,
        "duration_min": row.duration_min,
        "status": row.status,
        "version": row.version,
        "price_kopecks": row.price_kopecks,
        "currency": "UAH",
        "created_at": _iso(row.created_at),
        "expires_at": _iso(row.expires_at),
        "started_at": _iso(row.started_at),
        "finished_at": _iso(row.finished_at),
    }


def _bad_cursor(reason: str) -> ProblemError:
    return ProblemError(400, "invalid_cursor", "Invalid cursor",
                        f"Cursor is malformed ({reason}); start again without cursor")


@router.get("")
def list_cycles(
    user_id: Annotated[str, Depends(current_user_id)],
    conn: Annotated[Connection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
):
    params = {"user_id": user_id, "fetch": limit + 1}
    if cursor is None:
        sql = FIRST_PAGE_SQL
    else:
        try:
            after_t, after_id = decode_cursor(cursor)
        except InvalidCursor as exc:
            raise _bad_cursor(str(exc)) from exc
        sql = NEXT_PAGE_SQL
        params |= {"after_t": after_t, "after_id": after_id}

    try:
        rows = conn.exec_driver_sql(sql, params).all()
    except DataError as exc:  # напр., id у курсорі не відповідає типу стовпця
        conn.rollback()
        raise _bad_cursor("id has wrong format") from exc

    page = rows[:limit]
    has_more = len(rows) > limit
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if has_more else None
    return {"items": [_cycle_json(r) for r in page], "next_cursor": next_cursor}
