"""Підключення до PostgreSQL.

Адреса бази — змінна середовища DATABASE_URL, наприклад
postgresql+psycopg://laundry:laundry@localhost:5432/laundry
"""

import os
from collections.abc import Iterator

from sqlalchemy import Connection, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://laundry:laundry@localhost:5432/laundry"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_connection() -> Iterator[Connection]:
    """Залежність FastAPI: одне з'єднання на запит."""
    with engine.connect() as conn:
        yield conn
