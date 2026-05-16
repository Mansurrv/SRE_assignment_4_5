from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Problem:
  key: str
  message: str


def _parse_dotenv(path: Path) -> dict[str, str]:
  if not path.exists():
    return {}
  values: dict[str, str] = {}
  for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
      continue
    if "=" not in line:
      continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if key:
      values[key] = value
  return values


def _get_env(key: str, dotenv: dict[str, str]) -> str | None:
  return os.getenv(key) or dotenv.get(key)


def main() -> int:
  repo_root = Path(__file__).resolve().parents[1]
  dotenv = _parse_dotenv(repo_root / ".env")

  required = [
    "DATABASE_URL",
    "JWT_SECRET",
    "JWT_ISSUER",
    "PRODUCT_SERVICE_URL",
    "USER_SERVICE_URL",
    "PAYMENT_SERVICE_URL",
    "NOTIFICATION_SERVICE_URL",
  ]

  problems: list[Problem] = []
  for key in required:
    if not _get_env(key, dotenv):
      problems.append(Problem(key=key, message="missing"))

  jwt_secret = _get_env("JWT_SECRET", dotenv) or ""
  allow_dev = (_get_env("ALLOW_DEV_SECRETS", dotenv) or "").strip() == "1"
  if jwt_secret == "dev-secret-change-me" and not allow_dev:
    problems.append(
      Problem(
        key="JWT_SECRET",
        message="still set to dev-secret-change-me (set ALLOW_DEV_SECRETS=1 or change secret)",
      )
    )

  database_url = _get_env("DATABASE_URL", dotenv) or ""
  if database_url and not database_url.startswith("postgresql://"):
    problems.append(Problem(key="DATABASE_URL", message="must start with postgresql://"))

  for key in ("PRODUCT_SERVICE_URL", "USER_SERVICE_URL", "PAYMENT_SERVICE_URL", "NOTIFICATION_SERVICE_URL"):
    raw = _get_env(key, dotenv) or ""
    if not raw:
      continue
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
      problems.append(Problem(key=key, message="must be http:// or https:// URL"))
    if not parsed.netloc:
      problems.append(Problem(key=key, message="missing host:port"))

  if problems:
    sys.stderr.write("Environment preflight failed:\n")
    for p in problems:
      sys.stderr.write(f"- {p.key}: {p.message}\n")
    sys.stderr.write("\nTip: copy `.env.example` to `.env` and adjust values.\n")
    return 2

  print("Environment preflight OK.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
