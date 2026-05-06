from __future__ import annotations

import argparse
import random
import statistics
import threading
import time
from dataclasses import dataclass

import requests


@dataclass
class Result:
  ok: int = 0
  err: int = 0
  latencies_s: list[float] = None  # type: ignore[assignment]

  def __post_init__(self) -> None:
    if self.latencies_s is None:
      self.latencies_s = []


def _pct(values: list[float], p: float) -> float:
  if not values:
    return 0.0
  values_sorted = sorted(values)
  k = int(round((p / 100.0) * (len(values_sorted) - 1)))
  k = max(0, min(k, len(values_sorted) - 1))
  return values_sorted[k]


def _auth_token(base_url: str, email: str, password: str) -> str:
  resp = requests.post(
    f"{base_url}/api/auth/register",
    json={"email": email, "password": password, "full_name": "Load Test", "role": "customer"},
    timeout=10,
  )
  if resp.status_code not in (200, 409):
    raise RuntimeError(f"register failed: {resp.status_code} {resp.text}")

  resp = requests.post(
    f"{base_url}/api/auth/login",
    data={"username": email, "password": password},
    timeout=10,
  )
  resp.raise_for_status()
  return str(resp.json()["access_token"])


def _worker(
  *,
  base_url: str,
  token: str,
  user_email: str,
  stop_at: float,
  result: Result,
  lock: threading.Lock,
) -> None:
  headers = {"Authorization": f"Bearer {token}"}
  product_ids = [1, 2, 3, 4, 5]

  while time.time() < stop_at:
    payload = {
      "user_id": user_email,
      "items": [
        {"product_id": random.choice(product_ids), "quantity": random.randint(1, 3)},
        {"product_id": random.choice(product_ids), "quantity": random.randint(1, 3)},
      ],
    }
    started = time.perf_counter()
    try:
      resp = requests.post(f"{base_url}/api/orders/orders", json=payload, headers=headers, timeout=10)
      elapsed = time.perf_counter() - started
      with lock:
        result.latencies_s.append(elapsed)
        if resp.status_code == 200:
          result.ok += 1
        else:
          result.err += 1
    except Exception:
      elapsed = time.perf_counter() - started
      with lock:
        result.latencies_s.append(elapsed)
        result.err += 1


def main() -> int:
  parser = argparse.ArgumentParser(description="Simple load test for POST /orders.")
  parser.add_argument("--base-url", default="http://localhost:8080", help="Frontend base URL (default: http://localhost:8080)")
  parser.add_argument("--concurrency", type=int, default=10)
  parser.add_argument("--duration", type=int, default=30, help="Seconds")
  parser.add_argument("--email", default="loadtest@example.com")
  parser.add_argument("--password", default="pass")
  args = parser.parse_args()

  token = _auth_token(args.base_url, args.email, args.password)

  stop_at = time.time() + args.duration
  result = Result()
  lock = threading.Lock()
  threads = [
    threading.Thread(
      target=_worker,
      kwargs={
        "base_url": args.base_url,
        "token": token,
        "user_email": args.email,
        "stop_at": stop_at,
        "result": result,
        "lock": lock,
      },
      daemon=True,
    )
    for _ in range(args.concurrency)
  ]

  for t in threads:
    t.start()
  for t in threads:
    t.join()

  total = result.ok + result.err
  rps = total / max(args.duration, 1)
  lat = result.latencies_s
  p50 = _pct(lat, 50)
  p95 = _pct(lat, 95)
  avg = statistics.mean(lat) if lat else 0.0
  err_rate = (result.err / total) if total else 0.0

  print(f"requests_total={total} ok={result.ok} err={result.err} err_rate={err_rate:.3f} rps={rps:.1f}")
  print(f"latency_s avg={avg:.3f} p50={p50:.3f} p95={p95:.3f} max={max(lat) if lat else 0.0:.3f}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

