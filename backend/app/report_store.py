"""One SQLite row per daily scan.

Dated report-YYYY-MM-DD.json files used to pile up in the repo. New scans are
stored here (data/reports/reports.db) and can be fetched by run date. Legacy
JSON files are imported once, then removed.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "data" / "reports"
DB_PATH = REPORTS / "reports.db"

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_reports (
    run_date TEXT PRIMARY KEY,
    target_date TEXT,
    data_as_of TEXT,
    saved_at TEXT NOT NULL,
    pick_count INTEGER NOT NULL DEFAULT 0,
    payload TEXT NOT NULL
)
"""


def _connect():
    REPORTS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_SCHEMA)
    return conn


def save_report(report):
    """Insert or replace the full report for its run_date."""
    if not isinstance(report, dict):
        raise TypeError("report must be a dict")
    run_date = report.get("run_date")
    if not run_date:
        raise ValueError("report missing run_date")
    payload = json.dumps(report, default=str, separators=(",", ":"))
    saved_at = datetime.now(timezone.utc).isoformat()
    picks = report.get("picks") or []
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO daily_reports
                   (run_date, target_date, data_as_of, saved_at, pick_count, payload)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(run_date) DO UPDATE SET
                     target_date=excluded.target_date,
                     data_as_of=excluded.data_as_of,
                     saved_at=excluded.saved_at,
                     pick_count=excluded.pick_count,
                     payload=excluded.payload""",
                (
                    str(run_date),
                    report.get("target_date"),
                    report.get("data_as_of"),
                    saved_at,
                    len(picks),
                    payload,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return str(run_date)


def get_report(run_date):
    """Full report dict for one scan date, or None."""
    if not run_date:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT payload FROM daily_reports WHERE run_date = ?",
                (str(run_date),),
            ).fetchone()
        finally:
            conn.close()
    if not row:
        return None
    try:
        return json.loads(row["payload"])
    except Exception:
        return None


def delete_report(run_date) -> bool:
    """Delete a saved scan report for `run_date` from SQLite (e.g. when clearing
    today's predictions for a fresh scratch scan). Syncs latest.json to the new latest."""
    if not run_date:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM daily_reports WHERE run_date = ?",
                (str(run_date),),
            )
            conn.commit()
            deleted = cur.rowcount > 0
            row = conn.execute(
                "SELECT payload FROM daily_reports ORDER BY run_date DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    latest_path = REPORTS / "latest.json"
    try:
        if row:
            latest_path.write_text(row["payload"], encoding="utf-8")
        elif latest_path.exists():
            latest_path.unlink(missing_ok=True)
    except Exception:
        pass
    return deleted


def latest_report():
    """Newest scan by run_date, or None."""
    import_json_reports()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT payload FROM daily_reports ORDER BY run_date DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    if not row:
        return None
    try:
        return json.loads(row["payload"])
    except Exception:
        return None


def list_reports():
    """Every saved scan, newest first."""
    import_json_reports()
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT payload FROM daily_reports ORDER BY run_date DESC"
            ).fetchall()
        finally:
            conn.close()
    out = []
    for row in rows:
        try:
            out.append(json.loads(row["payload"]))
        except Exception:
            continue
    return out


def list_dates():
    """Scan dates only, newest first. Does not import JSON."""
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT run_date, target_date, pick_count FROM daily_reports ORDER BY run_date DESC"
            ).fetchall()
        finally:
            conn.close()
    return [
        {"run_date": r["run_date"], "target_date": r["target_date"], "pick_count": r["pick_count"]}
        for r in rows
    ]


def import_json_reports():
    """Copy legacy report-YYYY-MM-DD.json files into the database and delete them.

    backup-*.json and latest.json are left alone. Returns how many files were imported.
    """
    if not REPORTS.exists():
        return 0
    imported = 0
    for path in sorted(REPORTS.glob("report-*.json")):
        if not path.name.startswith("report-"):
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(report, dict) or not report.get("run_date"):
            continue
        save_report(report)
        try:
            path.unlink()
        except OSError:
            pass
        imported += 1
    return imported
