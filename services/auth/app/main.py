from datetime import datetime, timedelta, timezone
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import psycopg2
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from .db import db_conn


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "sre-assignment")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
  return datetime.now(timezone.utc)


def _create_access_token(*, subject: str, role: str) -> str:
  expires = _now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  payload: dict[str, Any] = {
    "iss": JWT_ISSUER,
    "sub": subject,
    "role": role,
    "iat": int(_now().timestamp()),
    "exp": int(expires.timestamp()),
  }
  return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"


class VerifyResponse(BaseModel):
  subject: str
  role: str
  issuer: str
  expires_at: int


class RegisterRequest(BaseModel):
  email: str
  password: str
  full_name: str = ""
  role: str = "customer"


app = FastAPI(title="Auth Service")

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
  with _http_request_duration_seconds.labels("auth-service", method, path).time():
    response = await call_next(request)
  _http_requests_total.labels("auth-service", method, path, str(response.status_code)).inc()
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
      # Concurrent CREATE TABLE IF NOT EXISTS can race during first boot. If another
      # service created it, treat as success.
      conn.rollback()
      return


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}

@app.get("/ready")
def ready() -> dict[str, str]:
  try:
    with db_conn() as conn, conn.cursor() as cur:
      cur.execute("SELECT 1")
      cur.fetchone()
  except Exception as exc:
    raise HTTPException(status_code=503, detail="Database not ready") from exc
  return {"status": "ready"}


@app.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "SELECT email, password_hash, role FROM users WHERE email = %s",
      (form.username.strip().lower(),),
    )
    row = cur.fetchone()
  if row is None:
    raise HTTPException(status_code=401, detail="Invalid credentials")
  email, password_hash, role = str(row[0]), str(row[1]), str(row[2])
  if not pwd_context.verify(form.password, password_hash):
    raise HTTPException(status_code=401, detail="Invalid credentials")
  token = _create_access_token(subject=email, role=role)
  return TokenResponse(access_token=token)


@app.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest) -> TokenResponse:
  role = (req.role or "").strip().lower()
  if role not in {"customer", "florist"}:
    raise HTTPException(status_code=400, detail="Invalid role")

  email = (req.email or "").strip().lower()
  if not email:
    raise HTTPException(status_code=400, detail="Invalid email")
  if not req.password:
    raise HTTPException(status_code=400, detail="Invalid password")

  password_hash = pwd_context.hash(req.password)
  try:
    with db_conn() as conn, conn.cursor() as cur:
      cur.execute(
        "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
        (email, password_hash, req.full_name or "", role),
      )
      conn.commit()
  except Exception as exc:
    raise HTTPException(status_code=409, detail="User already exists") from exc

  token = _create_access_token(subject=email, role=role)
  return TokenResponse(access_token=token)


@app.post("/verify", response_model=VerifyResponse)
def verify(token: TokenResponse) -> VerifyResponse:
  # Accepts: {"access_token": "...", "token_type": "bearer"}
  try:
    payload = jwt.decode(token.access_token, JWT_SECRET, algorithms=[ALGORITHM], issuer=JWT_ISSUER)
  except Exception as exc:
    raise HTTPException(status_code=401, detail="Invalid token") from exc
  return VerifyResponse(
    subject=str(payload.get("sub", "")),
    role=str(payload.get("role", "")),
    issuer=str(payload.get("iss", "")),
    expires_at=int(payload.get("exp", 0)),
  )
