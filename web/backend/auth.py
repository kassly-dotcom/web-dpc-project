"""Поточний користувач до ЛР3: заголовок X-User-Id із id заздалегідь створеного користувача."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import Connection

from .db import get_connection
from .problems import ProblemError


def current_user_id(
    conn: Annotated[Connection, Depends(get_connection)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    if not x_user_id or not x_user_id.strip():
        raise ProblemError(401, "unauthorized", "Unauthorized", "Header X-User-Id is required")
    user_id = x_user_id.strip()
    row = conn.exec_driver_sql(
        "SELECT 1 FROM users WHERE id::text = %(id)s", {"id": user_id}
    ).first()
    if row is None:
        raise ProblemError(401, "unauthorized", "Unauthorized", "Unknown user")
    return user_id
