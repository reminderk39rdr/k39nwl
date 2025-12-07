from __future__ import annotations

import ipaddress
import os
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "blocklist.db"
API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))  # requests per minute per client
RATE_WINDOW_SECONDS = 60
_rate_state: Dict[str, Tuple[float, float]] = {}  # client -> (tokens, timestamp)


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(f"Database not found at {DB_PATH}. Run scripts/build_blocklist_db.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def detect_type(value: str) -> str:
    try:
        ipaddress.ip_address(value)
        return "ip"
    except ValueError:
        return "domain"


app = FastAPI(title="Trust+ Blocklist API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: Optional[str] = Header(None)):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def enforce_rate_limit(request: Request):
    if RATE_LIMIT <= 0:
        return
    client = request.client.host if request.client else "unknown"
    tokens, last = _rate_state.get(client, (RATE_LIMIT, time.time()))
    now = time.time()
    elapsed = max(0.0, now - last)
    tokens = min(RATE_LIMIT, tokens + (elapsed * RATE_LIMIT / RATE_WINDOW_SECONDS))
    if tokens < 1.0:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _rate_state[client] = (tokens - 1.0, now)


@app.get("/health")
def health() -> Dict[str, str]:
    exists = DB_PATH.exists()
    return {"status": "ok" if exists else "missing_db", "db_path": str(DB_PATH)}


@app.get("/stats")
def stats():
    conn = get_connection()
    rows = conn.execute("SELECT source, entry_count, last_updated FROM sources ORDER BY source").fetchall()
    total_domains = conn.execute("SELECT COUNT(*) FROM entries WHERE type='domain'").fetchone()[0]
    total_ips = conn.execute("SELECT COUNT(*) FROM entries WHERE type='ip'").fetchone()[0]
    conn.close()
    failed_sources = [dict(row)["source"] for row in rows if dict(row).get("entry_count", 0) == 0]
    return {
        "sources": [dict(row) for row in rows],
        "totals": {"domains": total_domains, "ips": total_ips},
        "failed_sources": failed_sources,
    }


def lookup(values: List[str]) -> Dict[str, Dict[str, List[str]]]:
    if not values:
        raise HTTPException(status_code=400, detail="Provide at least one value via query or payload.")
    conn = get_connection()
    result: Dict[str, Dict[str, List[str]]] = {}
    for raw in values:
        value = raw.strip().lower()
        if not value:
            continue
        entry_type = detect_type(value)
        rows = conn.execute(
            "SELECT DISTINCT source FROM entries WHERE value = ?",
            (value,),
        ).fetchall()
        sources = [row["source"] for row in rows]
        result[value] = {"type": entry_type, "blocked": bool(sources), "sources": sources}
    conn.close()
    return result


@app.get("/check")
def check(
    request: Request,
    q: List[str] = Query(..., description="Repeated query parameter, e.g. ?q=domain1&q=domain2"),
    _: None = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
):
    """
    Query multiple domains/IPs: /check?q=example.com&q=1.2.3.4
    """
    return lookup(q)


class CheckRequest(BaseModel):
    items: List[str]


@app.post("/check")
def check_post(
    request: Request,
    body: CheckRequest,
    _: None = Depends(require_api_key),
    __: None = Depends(enforce_rate_limit),
):
    return lookup(body.items)
