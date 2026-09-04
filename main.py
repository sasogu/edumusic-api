"""EduMúsic Leaderboard API — replacement autoalojado del ranking en Firebase.

API REST mínima (FastAPI + SQLite) para las puntuaciones compartidas de
EduMúsic. Sustituye a Firebase Firestore (proyecto edumusic-f67e0).

Endpoints:
  GET  /api/health
  GET  /api/scores?game_id=X&period=all-time|weekly&limit=N
  POST /api/scores   { "game_id": "...", "name": "ABC", "score": 123 }
"""

import os
import re
import sqlite3
import threading
import time
import unicodedata
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, field_validator

DB_PATH = os.environ.get("EDUMUSIC_API_DB", "/var/lib/edumusic-api/leaderboard.db")
MAX_SCORE = 9999
MAX_LIMIT = 200
# Límite anti-abuso: nº de escrituras por IP y ventana (segundos).
RATE_WINDOW = 60
RATE_MAX = 60

app = FastAPI(title="EduMúsic Leaderboard API")

_rate_lock = threading.Lock()
_rate: dict[str, deque] = defaultdict(deque)


def _ensure_dir() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                name TEXT NOT NULL,
                score INTEGER NOT NULL,
                week_key TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scores_game "
            "ON scores(game_id, score DESC, created_at ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scores_week "
            "ON scores(game_id, week_key, score DESC, created_at ASC)"
        )


init_db()


def sanitize_game_id(raw: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (raw or "").lower()).strip("-")
    return s[:64]


def sanitize_name(raw: str) -> str:
    s = unicodedata.normalize("NFD", (raw or "").upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", s)[:3]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def week_key(dt: datetime) -> str:
    # Lunes 00:01 UTC, igual que getWeekKey() del cliente.
    monday = (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=1, second=0, microsecond=0
    )
    return monday.strftime("%Y-%m-%d")


def rate_limited(ip: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        q = _rate[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_MAX:
            return True
        q.append(now)
    return False


class ScoreIn(BaseModel):
    game_id: str
    name: str
    score: int

    @field_validator("score")
    @classmethod
    def _score_range(cls, v: int) -> int:
        if v < 0 or v > MAX_SCORE:
            raise ValueError("score out of range")
        return v


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/scores", status_code=201)
def add_score(payload: ScoreIn, request: Request) -> dict:
    if rate_limited(request.client.host if request.client else "?"):
        raise HTTPException(status_code=429, detail="too many requests")

    game_id = sanitize_game_id(payload.game_id)
    name = sanitize_name(payload.name)
    if not game_id:
        raise HTTPException(status_code=400, detail="invalid game_id")
    if len(name) != 3:
        raise HTTPException(status_code=400, detail="name must be 3 initials")

    now = now_utc()
    ts = now.isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scores (game_id, name, score, week_key, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (game_id, name, payload.score, week_key(now), ts),
        )
    return {"ok": True, "game_id": game_id, "name": name, "score": payload.score, "ts": ts}


@app.get("/api/scores")
def list_scores(
    game_id: str = Query(...),
    period: str = Query("all-time"),
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
) -> list[dict]:
    gid = sanitize_game_id(game_id)
    if not gid:
        raise HTTPException(status_code=400, detail="invalid game_id")
    if period not in ("all-time", "weekly"):
        raise HTTPException(status_code=400, detail="invalid period")

    if period == "weekly":
        wk = week_key(now_utc())
        sql = (
            "SELECT name, score, created_at FROM scores "
            "WHERE game_id = ? AND week_key = ? "
            "ORDER BY score DESC, created_at ASC LIMIT ?"
        )
        args = (gid, wk, limit)
    else:
        sql = (
            "SELECT name, score, created_at FROM scores "
            "WHERE game_id = ? "
            "ORDER BY score DESC, created_at ASC LIMIT ?"
        )
        args = (gid, limit)

    with get_conn() as conn:
        rows = conn.execute(sql, args).fetchall()

    return [{"name": r["name"], "score": r["score"], "ts": r["created_at"]} for r in rows]
