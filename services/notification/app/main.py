from __future__ import annotations

import os
import time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


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


class NotifyRequest(BaseModel):
  user_id: str = Field(min_length=3, max_length=320)
  order_id: str = Field(min_length=3, max_length=128)
  message: str = Field(min_length=1, max_length=500)


class NotificationRecord(BaseModel):
  id: str
  user_id: str
  order_id: str
  message: str
  created_at_ms: int


app = FastAPI(title="Notification Service")

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

_notifications: list[NotificationRecord] = []


@app.middleware("http")
async def _metrics_middleware(request, call_next):
  method = request.method
  path = request.url.path
  with _http_request_duration_seconds.labels("notification-service", method, path).time():
    response = await call_next(request)
  _http_requests_total.labels("notification-service", method, path, str(response.status_code)).inc()
  return response


@app.get("/metrics")
def metrics() -> Response:
  return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health() -> dict[str, str]:
  return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
  return {"status": "ready"}


@app.post("/notify", response_model=NotificationRecord)
def notify(
  req: NotifyRequest,
  identity: Annotated[tuple[str, str], Depends(require_subject)],
) -> NotificationRecord:
  subject, role = identity
  if role == "customer" and req.user_id != subject:
    raise HTTPException(status_code=403, detail="Cannot notify other users")

  record = NotificationRecord(
    id=f"msg_{int(time.time() * 1000)}",
    user_id=req.user_id,
    order_id=req.order_id,
    message=req.message,
    created_at_ms=int(time.time() * 1000),
  )
  _notifications.insert(0, record)
  if len(_notifications) > 200:
    del _notifications[200:]
  return record


@app.get("/notifications", response_model=list[NotificationRecord])
def list_notifications(identity: Annotated[tuple[str, str], Depends(require_subject)]) -> list[NotificationRecord]:
  _subject, role = identity
  if role != "florist":
    raise HTTPException(status_code=403, detail="Florist role required")
  return _notifications

