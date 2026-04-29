from __future__ import annotations

import os
import time
from typing import Annotated

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from .db import db_conn


PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8003")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8002")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "sre-assignment")
ALGORITHM = "HS256"

bearer = HTTPBearer(auto_error=False)


def require_subject(
  credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[str, str, str]:
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
  return subject, role, credentials.credentials


class OrderItemIn(BaseModel):
  product_id: int
  quantity: int = Field(ge=1, le=100)


class CreateOrderRequest(BaseModel):
  user_id: str
  items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
  product_id: int
  quantity: int
  unit_price_cents: int
  line_total_cents: int


class OrderOut(BaseModel):
  id: str
  user_id: str
  created_at_ms: int
  total_cents: int
  items: list[OrderItemOut]


app = FastAPI(title="Order Service")

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
  with _http_request_duration_seconds.labels("order-service", method, path).time():
    response = await call_next(request)
  _http_requests_total.labels("order-service", method, path, str(response.status_code)).inc()
  return response


@app.get("/metrics")
def metrics() -> Response:
  return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
def _ensure_schema() -> None:
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_email TEXT NOT NULL REFERENCES users(email) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        total_cents INTEGER NOT NULL CHECK (total_cents >= 0)
      )
      """
    )
    cur.execute(
      """
      CREATE TABLE IF NOT EXISTS order_items (
        order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
        quantity INTEGER NOT NULL CHECK (quantity >= 1),
        unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
        PRIMARY KEY (order_id, product_id)
      )
      """
    )
    conn.commit()


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}


def _get_product_price_cents(*, product_id: int, bearer_token: str) -> int:
  # Demonstrates inter-service HTTP: order -> product
  try:
    resp = requests.get(
      f"{PRODUCT_SERVICE_URL}/products/{product_id}",
      headers={"Authorization": f"Bearer {bearer_token}"},
      timeout=3,
    )
  except requests.RequestException as exc:
    raise HTTPException(status_code=502, detail="Product service unreachable") from exc
  if resp.status_code == 404:
    raise HTTPException(status_code=400, detail=f"Unknown product_id={product_id}")
  if resp.status_code != 200:
    raise HTTPException(status_code=502, detail="Product service error")
  payload = resp.json()
  return int(payload["price_cents"])


def _ensure_user_exists(*, user_id: str, bearer_token: str) -> None:
  # Demonstrates inter-service HTTP: order -> user
  try:
    resp = requests.get(
      f"{USER_SERVICE_URL}/users/{user_id}",
      headers={"Authorization": f"Bearer {bearer_token}"},
      timeout=3,
    )
  except requests.RequestException as exc:
    raise HTTPException(status_code=502, detail="User service unreachable") from exc
  if resp.status_code == 404:
    raise HTTPException(status_code=400, detail=f"Unknown user_id={user_id}")
  if resp.status_code != 200:
    raise HTTPException(status_code=502, detail="User service error")


@app.get("/orders", response_model=list[OrderOut])
def list_orders(identity: Annotated[tuple[str, str, str], Depends(require_subject)]) -> list[OrderOut]:
  subject, role, _token = identity
  with db_conn() as conn, conn.cursor() as cur:
    if role == "florist":
      cur.execute(
        "SELECT id, user_email, created_at, total_cents FROM orders ORDER BY created_at DESC LIMIT 200"
      )
    else:
      cur.execute(
        "SELECT id, user_email, created_at, total_cents FROM orders WHERE user_email = %s ORDER BY created_at DESC LIMIT 200",
        (subject,),
      )
    orders_rows = cur.fetchall()

    results: list[OrderOut] = []
    for order_id, user_email, created_at, total_cents in orders_rows:
      cur.execute(
        "SELECT product_id, quantity, unit_price_cents FROM order_items WHERE order_id = %s ORDER BY product_id ASC",
        (order_id,),
      )
      item_rows = cur.fetchall()
      items_out: list[OrderItemOut] = []
      for product_id, quantity, unit_price_cents in item_rows:
        line_total = int(unit_price_cents) * int(quantity)
        items_out.append(
          OrderItemOut(
            product_id=int(product_id),
            quantity=int(quantity),
            unit_price_cents=int(unit_price_cents),
            line_total_cents=line_total,
          )
        )
      results.append(
        OrderOut(
          id=str(order_id),
          user_id=str(user_email),
          created_at_ms=int(created_at.timestamp() * 1000),
          total_cents=int(total_cents),
          items=items_out,
        )
      )
  return results


@app.post("/orders", response_model=OrderOut)
def create_order(
  req: CreateOrderRequest,
  identity: Annotated[tuple[str, str, str], Depends(require_subject)],
) -> OrderOut:
  subject, role, token = identity
  if role != "customer":
    raise HTTPException(status_code=403, detail="Customer role required")
  if req.user_id != subject:
    raise HTTPException(status_code=403, detail="Cannot create orders for other users")

  _ensure_user_exists(user_id=req.user_id, bearer_token=token)

  items_out: list[OrderItemOut] = []
  total = 0
  for item in req.items:
    unit_price = _get_product_price_cents(product_id=item.product_id, bearer_token=token)
    line_total = unit_price * item.quantity
    total += line_total
    items_out.append(
      OrderItemOut(
        product_id=item.product_id,
        quantity=item.quantity,
        unit_price_cents=unit_price,
        line_total_cents=line_total,
      )
    )

  order_id = f"ord_{int(time.time() * 1000)}"
  created_at_ms = int(time.time() * 1000)

  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "INSERT INTO orders (id, user_email, total_cents) VALUES (%s, %s, %s)",
      (order_id, req.user_id, total),
    )
    for item in items_out:
      cur.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (%s, %s, %s, %s)",
        (order_id, item.product_id, item.quantity, item.unit_price_cents),
      )
    conn.commit()

  return OrderOut(
    id=order_id,
    user_id=req.user_id,
    created_at_ms=created_at_ms,
    total_cents=total,
    items=items_out,
  )
