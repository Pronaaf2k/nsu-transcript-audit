from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def probe(path: str) -> None:
    url = f"{BACKEND_URL}{path}"
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)
        print(f"{path}: {response.status_code}")
    except Exception as exc:
        print(f"{path}: unavailable ({exc})")


if __name__ == "__main__":
    print(f"BACKEND_URL={BACKEND_URL}")
    probe("/health")
    probe("/docs")
    probe("/openapi.json")
