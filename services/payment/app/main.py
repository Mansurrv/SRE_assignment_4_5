from __future__ import annotations

import os
import random
import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from .db import db_conn


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "sre-assignment")
ALGORITHM = "HS256"

PAYMENT_FAIL_RATE = float(os.getenv("PAYMENT_FAIL_RATE", "0.0"))
PAYMENT_LATENCY_MS = int(os.getenv("PAYMENT_LATENCY_MS", "30"))

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


class PayRequest(BaseModel):
  order_id: str = Field(min_length=3, max_length=128)
  user_id: str = Field(min_length=3, max_length=320)
  amount_cents: int = Field(ge=0, le=10_000_000)


class PayResponse(BaseModel):
  payment_id: str
  order_id: str
  status: str
  processed_at_ms: int


class PaymentRecord(BaseModel):
  id: str
  order_id: str
  user_id: str
  amount_cents: int
  status: str
  created_at_ms: int


app = FastAPI(title="Payment Service")

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
  with _http_request_duration_seconds.labels("payment-service", method, path).time():
    response = await call_next(request)
  _http_requests_total.labels("payment-service", method, path, str(response.status_code)).inc()
  return response


@app.get("/metrics")
def metrics() -> Response:
  return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
def _ensure_schema() -> None:
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        user_email TEXT NOT NULL REFERENCES users(email) ON DELETE RESTRICT,
        amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
        status TEXT NOT NULL CHECK (status IN ('approved', 'declined')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      )
      """
    )
    conn.commit()


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


@app.post("/pay", response_model=PayResponse)
def pay(
  req: PayRequest,
  identity: Annotated[tuple[str, str], Depends(require_subject)],
) -> PayResponse:
  subject, role = identity
  if role != "customer":
    raise HTTPException(status_code=403, detail="Customer role required")
  if req.user_id != subject:
    raise HTTPException(status_code=403, detail="Cannot pay for other users")

  if PAYMENT_LATENCY_MS > 0:
    time.sleep(PAYMENT_LATENCY_MS / 1000.0)

  status = "approved"
  if PAYMENT_FAIL_RATE > 0 and random.random() < PAYMENT_FAIL_RATE:
    status = "declined"

  payment_id = f"pay_{int(time.time() * 1000)}"
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "INSERT INTO payments (id, order_id, user_email, amount_cents, status) VALUES (%s, %s, %s, %s, %s)",
      (payment_id, req.order_id, req.user_id, req.amount_cents, status),
    )
    conn.commit()

  if status != "approved":
    raise HTTPException(status_code=402, detail="Payment declined")

  return PayResponse(
    payment_id=payment_id,
    order_id=req.order_id,
    status=status,
    processed_at_ms=int(time.time() * 1000),
  )


@app.get("/payments", response_model=list[PaymentRecord])
def list_payments(identity: Annotated[tuple[str, str], Depends(require_subject)]) -> list[PaymentRecord]:
  _subject, role = identity
  if role != "florist":
    raise HTTPException(status_code=403, detail="Florist role required")

  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "SELECT id, order_id, user_email, amount_cents, status, created_at FROM payments ORDER BY created_at DESC LIMIT 200"
    )
    rows = cur.fetchall()

  results: list[PaymentRecord] = []
  for pid, order_id, user_email, amount_cents, status, created_at in rows:
    results.append(
      PaymentRecord(
        id=str(pid),
        order_id=str(order_id),
        user_id=str(user_email),
        amount_cents=int(amount_cents),
        status=str(status),
        created_at_ms=int(created_at.timestamp() * 1000),
      )
    )
  return results
