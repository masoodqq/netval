"""SQLite storage for test runs. Swap for PostgreSQL in phase 3."""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = os.getenv("NETVAL_DB", "netval.db")
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan TEXT, status TEXT, created_at TEXT, finished_at TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS device_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER, host TEXT, serial TEXT, passed INTEGER,
                error TEXT, checks TEXT, duration_s REAL)"""
        )


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_run(plan: str) -> int:
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO runs (plan, status, created_at) VALUES (?, 'running', ?)", (plan, now())
        )
        return cur.lastrowid


def finish_run(run_id: int, status: str) -> None:
    with _lock, _conn() as c:
        c.execute("UPDATE runs SET status=?, finished_at=? WHERE id=?", (status, now(), run_id))


def add_result(run_id: int, r: dict) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO device_results (run_id, host, serial, passed, error, checks, duration_s)"
            " VALUES (?,?,?,?,?,?,?)",
            (run_id, r["host"], r.get("serial"), int(r["passed"]), r.get("error"),
             json.dumps(r.get("checks", [])), r["duration_s"]),
        )


def get_run(run_id: int) -> dict | None:
    with _conn() as c:
        run = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not run:
            return None
        rows = c.execute("SELECT * FROM device_results WHERE run_id=?", (run_id,)).fetchall()
    devices = [{**dict(r), "passed": bool(r["passed"]), "checks": json.loads(r["checks"])} for r in rows]
    passed = sum(d["passed"] for d in devices)
    return {**dict(run), "summary": {"total": len(devices), "passed": passed,
                                     "failed": len(devices) - passed}, "devices": devices}


def list_runs(limit: int = 50) -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
