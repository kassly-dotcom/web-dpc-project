"""Підключення до PostgreSQL.

Адреса бази — змінна середовища DATABASE_URL, наприклад
postgresql+psycopg://app:app@localhost:5434/laundry_web
"""

import os
from collections.abc import Iterator

from sqlalchemy import Connection, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://app:app@localhost:5434/laundry_web"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_connection() -> Iterator[Connection]:
    """Залежність FastAPI: одне з'єднання на запит."""
    with engine.connect() as conn:
        yield conn
