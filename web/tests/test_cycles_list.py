"""О1.5. GET /v1/cycles на справжньому PostgreSQL.

Потрібна порожня тестова база в TEST_DATABASE_URL, наприклад:
  docker run -d --name laundry-test-db -e POSTGRES_USER=laundry -e POSTGRES_PASSWORD=laundry \
      -e POSTGRES_DB=laundry_test -p 55432:5432 postgres:17
  $env:TEST_DATABASE_URL = "postgresql+psycopg://laundry:laundry@localhost:55432/laundry_test"
Без змінної тести пропускаються.

Тести самі створюють мінімальні таблиці users/machines/cycles у схемі o15_test.
Після злиття О1.2 їх варто перевести на справжні міграції.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL is not set")

if TEST_DB:
    sep = "&" if "?" in TEST_DB else "?"
    os.environ["DATABASE_URL"] = f"{TEST_DB}{sep}options=-csearch_path%3Do15_test"

SCHEMA = """
DROP SCHEMA IF EXISTS o15_test CASCADE;
CREATE SCHEMA o15_test;
SET search_path TO o15_test;
CREATE TABLE users (id bigint PRIMARY KEY, name text NOT NULL, role text NOT NULL);
CREATE TABLE machines (id bigint PRIMARY KEY);
CREATE TABLE cycles (
    id uuid PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(id),
    machine_id bigint NOT NULL REFERENCES machines(id),
    program text NOT NULL,
    duration_min integer NOT NULL,
    status text NOT NULL,
    version integer NOT NULL DEFAULT 1,
    price_kopecks bigint NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    started_at timestamptz,
    finished_at timestamptz
);
CREATE INDEX cycles_user_page ON cycles (user_id, created_at DESC, id DESC);
INSERT INTO users VALUES (1, 'Olena', 'student'), (2, 'Taras', 'student');
INSERT INTO machines VALUES (1), (2);
"""

T0 = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    from web.backend.db import engine

    with engine.begin() as conn:
        conn.exec_driver_sql(SCHEMA)
    yield engine


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from web.backend.main import app

    return TestClient(app)


def add_cycle(engine, user_id: int, created_at: datetime, cycle_id: str | None = None) -> str:
    cycle_id = cycle_id or str(uuid.uuid4())
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """INSERT INTO cycles (id, user_id, machine_id, program, duration_min, status,
                                   price_kopecks, created_at, expires_at)
               VALUES (%(id)s, %(u)s, 1, 'standard_wash', 60, 'done', 5000, %(t)s, %(e)s)""",
            {"id": cycle_id, "u": user_id, "t": created_at, "e": created_at + timedelta(minutes=10)},
        )
    return cycle_id


def read_all(client, user="1", limit=2):
    ids, cursor, pages = [], None, 0
    while True:
        params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
        r = client.get("/v1/cycles", params=params, headers={"X-User-Id": user})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) <= limit
        ids += [c["id"] for c in body["items"]]
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            return ids, pages


def expected_order(engine, user_id=1):
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT id FROM cycles WHERE user_id = %(u)s ORDER BY created_at DESC, id DESC",
            {"u": user_id},
        ).all()
    return [str(r.id) for r in rows]


def test_all_pages_without_duplicates_or_gaps_with_equal_times(client, db):
    # 3 цикли з ОДНАКОВИМ created_at — саме тут курсор лише за часом загубив би рядки.
    for _ in range(3):
        add_cycle(db, 1, T0)
    for k in range(1, 5):
        add_cycle(db, 1, T0 - timedelta(minutes=k))
    ids, pages = read_all(client, limit=2)
    assert ids == expected_order(db)
    assert len(ids) == 7 and len(set(ids)) == 7
    assert pages == 4


def test_insert_between_pages_does_not_shift_next_page(client, db):
    for k in range(5):
        add_cycle(db, 1, T0 - timedelta(minutes=k))
    before = expected_order(db)

    r1 = client.get("/v1/cycles", params={"limit": 2}, headers={"X-User-Id": "1"}).json()
    add_cycle(db, 1, T0 + timedelta(minutes=1))  # новий найновіший цикл під час гортання
    r2 = client.get("/v1/cycles", params={"limit": 2, "cursor": r1["next_cursor"]},
                    headers={"X-User-Id": "1"}).json()

    seen = [c["id"] for c in r1["items"] + r2["items"]]
    assert seen == before[:4]  # жодного дубля (з offset тут повторився б рядок)


def test_only_own_cycles(client, db):
    mine = add_cycle(db, 1, T0)
    add_cycle(db, 2, T0 + timedelta(minutes=1))
    ids, _ = read_all(client, user="1", limit=50)
    assert ids == [mine]


def test_empty_list(client, db):
    r = client.get("/v1/cycles", headers={"X-User-Id": "1"})
    assert r.status_code == 200
    assert r.json() == {"items": [], "next_cursor": None}


def test_item_shape_matches_contract(client, db):
    add_cycle(db, 1, T0)
    item = client.get("/v1/cycles", headers={"X-User-Id": "1"}).json()["items"][0]
    assert set(item) == {"id", "machine_id", "program", "duration_min", "status", "version",
                         "price_kopecks", "currency", "created_at", "expires_at",
                         "started_at", "finished_at"}
    assert isinstance(item["id"], str) and isinstance(item["machine_id"], str)
    assert item["created_at"] == "2026-11-18T12:00:00Z"
    assert item["currency"] == "UAH"


@pytest.mark.parametrize("cursor", ["garbage", "eyJ0IjoxfQ", "e30"])
def test_corrupted_cursor_gives_400_problem(client, db, cursor):
    r = client.get("/v1/cycles", params={"cursor": cursor}, headers={"X-User-Id": "1"})
    assert r.status_code == 400
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "invalid_cursor"


def test_cursor_with_wrong_id_type_gives_400(client, db):
    from web.backend.cursor import encode_cursor

    bad = encode_cursor(T0, "not-a-uuid")
    r = client.get("/v1/cycles", params={"cursor": bad}, headers={"X-User-Id": "1"})
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_cursor"


@pytest.mark.parametrize("limit", [0, 51, "abc"])
def test_limit_out_of_range_gives_422_problem(client, db, limit):
    r = client.get("/v1/cycles", params={"limit": limit}, headers={"X-User-Id": "1"})
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "validation_error"
    assert body["errors"][0]["field"] == "query.limit"


@pytest.mark.parametrize("headers", [{}, {"X-User-Id": "999"}, {"X-User-Id": "abc"}])
def test_missing_or_unknown_user_gives_401(client, db, headers):
    r = client.get("/v1/cycles", headers=headers)
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"
