#!/usr/bin/env python3
"""Read-only staging smoke checks for XGetawaySX API and optional frontend routes."""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE_URL = os.environ.get("API_BASE_URL", "").strip().rstrip("/")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").strip().rstrip("/")
TIMEOUT_SECONDS = 20

API_ENDPOINTS = (
    ("health", "/api/v1/health/"),
    ("database readiness", "/api/v1/health/ready/"),
    ("partners", "/api/v1/partners/"),
    ("destinations", "/api/v1/partners/destinations/"),
    ("collections", "/api/v1/partners/collections/"),
    ("public Gallery stories", "/api/v1/gallery/stories/"),
)
FRONTEND_PATHS = (
    "/",
    "/gallery/",
    "/partner/gallery/",
    "/staff/gallery/editorial/",
)


def fetch(url: str) -> tuple[int, bytes]:
    request = Request(url, headers={"Accept": "application/json, text/html"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except HTTPError as error:
        body = error.read()
        raise RuntimeError(f"HTTP {error.code} from {url}: {body[:300].decode('utf-8', 'replace')}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach {url}: {error}") from error


def check_api() -> list[str]:
    if not API_BASE_URL.startswith(("https://", "http://")):
        raise RuntimeError("Set API_BASE_URL to the staging API origin.")
    passed: list[str] = []
    for label, path in API_ENDPOINTS:
        url = API_BASE_URL + path
        status, body = fetch(url)
        if not 200 <= status < 300:
            raise RuntimeError(f"{label}: expected 2xx, received {status}")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"{label}: response was not valid JSON") from error

        if label == "database readiness":
            if not isinstance(payload, dict) or payload.get("status") != "ready" or payload.get("database") != "connected":
                raise RuntimeError(f"database readiness: unexpected payload {payload!r}")
        if label == "public Gallery stories":
            is_list = isinstance(payload, list)
            is_paginated_list = isinstance(payload, dict) and isinstance(payload.get("results"), list)
            if not (is_list or is_paginated_list):
                raise RuntimeError("public Gallery stories: expected a list or paginated results list")
            count = len(payload if is_list else payload["results"])
            print(f"PASS {label}: HTTP {status}, {count} publicly approved stories")
        else:
            print(f"PASS {label}: HTTP {status}, valid JSON")
        passed.append(label)
    return passed


def check_frontend() -> list[str]:
    if not FRONTEND_BASE_URL:
        print("SKIP frontend routes: FRONTEND_BASE_URL was not supplied")
        return []
    if not FRONTEND_BASE_URL.startswith(("https://", "http://")):
        raise RuntimeError("FRONTEND_BASE_URL must be an HTTP(S) origin.")
    passed: list[str] = []
    for path in FRONTEND_PATHS:
        status, _ = fetch(FRONTEND_BASE_URL + path)
        if not 200 <= status < 300:
            raise RuntimeError(f"frontend {path}: expected 2xx, received {status}")
        print(f"PASS frontend {path}: HTTP {status}")
        passed.append(path)
    return passed


def main() -> int:
    try:
        api_passed = check_api()
        frontend_passed = check_frontend()
    except RuntimeError as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"\nStaging smoke checks passed: {len(api_passed)} API endpoints, {len(frontend_passed)} frontend routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
