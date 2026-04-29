import os
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


def require_florist(identity: Annotated[tuple[str, str], Depends(require_subject)]) -> tuple[str, str]:
  subject, role = identity
  if role != "florist":
    raise HTTPException(status_code=403, detail="Florist role required")
  return subject, role


class Product(BaseModel):
  id: int
  sku: str
  name: str
  description: str
  price_cents: int


class ProductUpsert(BaseModel):
  sku: str = Field(min_length=1, max_length=64)
  name: str = Field(min_length=1, max_length=200)
  description: str = Field(default="")
  price_cents: int = Field(ge=0, le=10_000_000)


app = FastAPI(title="Product Service")

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
  with _http_request_duration_seconds.labels("product-service", method, path).time():
    response = await call_next(request)
  _http_requests_total.labels("product-service", method, path, str(response.status_code)).inc()
  return response


@app.get("/metrics")
def metrics() -> Response:
  return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}


@app.get("/products", response_model=list[Product])
def list_products(identity: Annotated[tuple[str, str], Depends(require_subject)]) -> list[Product]:
  _subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "SELECT id, sku, name, description, price_cents FROM products ORDER BY id ASC LIMIT 200"
    )
    rows = cur.fetchall()
  return [Product(id=r[0], sku=r[1], name=r[2], description=r[3], price_cents=r[4]) for r in rows]


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, identity: Annotated[tuple[str, str], Depends(require_subject)]) -> Product:
  _subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "SELECT id, sku, name, description, price_cents FROM products WHERE id = %s",
      (product_id,),
    )
    row = cur.fetchone()
  if row is None:
    raise HTTPException(status_code=404, detail="Product not found")
  return Product(id=row[0], sku=row[1], name=row[2], description=row[3], price_cents=row[4])


@app.post("/products", response_model=Product, status_code=201)
def create_product(
  req: ProductUpsert,
  identity: Annotated[tuple[str, str], Depends(require_florist)],
) -> Product:
  _subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "INSERT INTO products (sku, name, description, price_cents) VALUES (%s, %s, %s, %s) RETURNING id, sku, name, description, price_cents",
      (req.sku, req.name, req.description, req.price_cents),
    )
    row = cur.fetchone()
    conn.commit()
  return Product(id=int(row[0]), sku=str(row[1]), name=str(row[2]), description=str(row[3]), price_cents=int(row[4]))


@app.put("/products/{product_id}", response_model=Product)
def update_product(
  product_id: int,
  req: ProductUpsert,
  identity: Annotated[tuple[str, str], Depends(require_florist)],
) -> Product:
  _subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute(
      "UPDATE products SET sku = %s, name = %s, description = %s, price_cents = %s WHERE id = %s RETURNING id, sku, name, description, price_cents",
      (req.sku, req.name, req.description, req.price_cents, product_id),
    )
    row = cur.fetchone()
    conn.commit()
  if row is None:
    raise HTTPException(status_code=404, detail="Product not found")
  return Product(id=int(row[0]), sku=str(row[1]), name=str(row[2]), description=str(row[3]), price_cents=int(row[4]))


@app.delete("/products/{product_id}", status_code=204)
def delete_product(
  product_id: int,
  identity: Annotated[tuple[str, str], Depends(require_florist)],
) -> None:
  _subject, _role = identity
  with db_conn() as conn, conn.cursor() as cur:
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    deleted = cur.rowcount
    conn.commit()
  if deleted == 0:
    raise HTTPException(status_code=404, detail="Product not found")
  return None
