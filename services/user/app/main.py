import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel
import psycopg2
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from .db import db_conn


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "sre-assignment")
ALGORITHM = "HS256"

bearer = HTTPBearer(auto_error=False)


def require_subject(
  credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[str, str]:
  if credentials is None:
    raise HTTPException(status_code=401, detail="Missing Authorization header")
  if credentials.scheme.lower() != "bearer":
    raise HTTPException(status_code=401, detail="Unsupported auth scheme")
  try:
    payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM], issuer=JWT_ISSUER)
  except Exception as exc:
    raise HTTPException(status_code=401, detail="Invalid token") from exc
  subject = str(payload.get("sub") or "")
  if not subject:
    raise HTTPException(status_code=401, detail="Invalid token subject")
  role = str(payload.get("role") or "")
  return subject, role


class UserProfile(BaseModel):
  id: str
  email: str
  full_name: str
  role: str


class UpdateProfile(BaseModel):
  full_name: str


app = FastAPI(title="User Service")

_http_requests_total = Counter(
  "http_requests_total",
  "Total HTTP requests",
  ["service", "method", "path", "status"],
)
_http_request_duration_seconds = Histogram(
  "http_request_duration_seconds",
  "HTTP request duration in seconds",
  ["service", "method", "path"],
)


@app.middleware("http")
async def _metrics_middleware(request, call_next):
  method = request.method
  path = request.url.path
  with _http_request_duration_seconds.labels("user-service", method, path).time():
    response = await call_next(request)
  _http_requests_total.labels("user-service", method, path, str(response.status_code)).inc()
  return response


@app.get("/metrics")
def metrics() -> Response:
  return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
def _ensure_schema() -> None:
  with db_conn() as conn, conn.cursor() as cur:
    try:
      cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          email TEXT PRIMARY KEY,
          password_hash TEXT NOT NULL,
          full_name TEXT NOT NULL DEFAULT '',
          role TEXT NOT NULL CHECK (role IN ('customer', 'florist')),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
      )
      conn.commit()
    except psycopg2.Error:
      conn.rollback()
      return


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}

@app.get("/healthz")
def healthz() -> dict[str, str]:
  return health()

@app.get("/ready")
def ready() -> dict[str, str]:
  try:
    with db_conn() as conn, conn.cursor() as cur:
      cur.execute("SELECT 1")
      cur.fetchone()
  except Exception as exc:
    raise HTTPException(status_code=503, detail="Database not ready") from exc
  return {"status": "ready"}


@app.get("/me", response_model=UserProfile)
def me(identity: Annotated[tuple[str, str], Depends(require_subject)]) -> UserProfile:
  subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute("SELECT email, full_name, role FROM users WHERE email = %s", (subject,))
    row = cur.fetchone()
  if row is None:
    raise HTTPException(status_code=404, detail="User not found")
  return UserProfile(id=str(row[0]), email=str(row[0]), full_name=str(row[1]), role=str(row[2]))


@app.get("/users/{user_id}", response_model=UserProfile)
def get_user(user_id: str, identity: Annotated[tuple[str, str], Depends(require_subject)]) -> UserProfile:
  subject, role = identity
  if role == "customer" and user_id != subject:
    raise HTTPException(status_code=403, detail="Forbidden")
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute("SELECT email, full_name, role FROM users WHERE email = %s", (user_id,))
    row = cur.fetchone()
  if row is None:
    raise HTTPException(status_code=404, detail="User not found")
  return UserProfile(id=str(row[0]), email=str(row[0]), full_name=str(row[1]), role=str(row[2]))


@app.put("/me", response_model=UserProfile)
def update_me(
  update: UpdateProfile,
  identity: Annotated[tuple[str, str], Depends(require_subject)],
) -> UserProfile:
  subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute("UPDATE users SET full_name = %s WHERE email = %s RETURNING email, full_name, role", (update.full_name, subject))
    row = cur.fetchone()
    conn.commit()
  if row is None:
    raise HTTPException(status_code=404, detail="User not found")
  return UserProfile(id=str(row[0]), email=str(row[0]), full_name=str(row[1]), role=str(row[2]))
