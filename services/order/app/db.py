import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection as Connection


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:5432/app")


@contextmanager
def db_conn() -> Iterator[Connection]:
  conn = psycopg2.connect(DATABASE_URL)
  try:
    yield conn
  finally:
    conn.close()

