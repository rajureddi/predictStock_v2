"""Start the day's prediction before the NSE open and email it when it finishes.

A full scan takes about 30–60 minutes. Starting at 07:00 IST on each weekday
leaves that hour and still sends the mail before the 09:15 cash open. Saturday
and Sunday stay quiet because the cash market is closed. The computer has to
be on, with this app running, at 07:00.
"""
import json
import time
from datetime import datetime, time as dtime
from pathlib import Path

from app.alerts import IST, ist_now

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data" / "morning_state.json"
START = dtime(7, 0)
OPEN = dtime(9, 15)


def schedule():
    """Times saved on Alerts & mail. Defaults stay 07:00 and 09:15."""
    from app import mailer
    cfg = mailer.public_config()
    def as_time(value, fallback):
        hour, minute = (value or fallback).split(":")
        return dtime(int(hour), int(minute))
    return as_time(cfg.get("scan_start"), "07:00"), as_time(cfg.get("email_by"), "09:15")


def decide(now, state, scan_running, report_date, start_at=None, email_by=None):
    """Pure decision. Weekdays only. Start inside the saved window. Send after the scan, even if it finishes after the deadline."""
    n = ist_now(now)
    today = n.date().isoformat()
    state = dict(state or {})
    if state.get("date") != today:
        state = {"date": today, "started": False, "emailed": False}
    start_at = start_at or START
    email_by = email_by or OPEN
    start = False
    send = False
    if n.weekday() < 5 and not state.get("started"):
        if report_date == today:
            state["started"] = True
        elif scan_running or (start_at <= n.time() < email_by):
            if not scan_running and start_at <= n.time() < email_by:
                start = True
            state["started"] = True
    if state.get("started") and not state.get("emailed") and not scan_running and report_date == today:
        send = True
    return {"start": start, "send": send, "state": state}


def load_state():
    try:
        if STATE_PATH.exists():
            doc = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(doc, dict):
                return doc
    except Exception:
        pass
    return {}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")


def status(now=None):
    n = ist_now(now)
    state = load_state()
    start_at, email_by = schedule()
    return {
        "scan_start": start_at.strftime("%H:%M"),
        "email_by": email_by.strftime("%H:%M"),
        "alerts_from": email_by.strftime("%H:%M"),
        "alerts_until": "16:00",
        "start": f"Weekdays {start_at.strftime('%H:%M')} IST",
        "email_before": f"{email_by.strftime('%H:%M')} IST",
        "scan_minutes": "30–60",
        "now": n.strftime("%Y-%m-%d %H:%M IST"),
        "today": state if state.get("date") == n.date().isoformat() else None,
    }


WATCH_UNTIL = dtime(16, 0)


def _arm_alerts(report):
    from app import alerts
    alerts.sync_from_picks((report or {}).get("picks") or [])


def _watch_alerts():
    """Email each new stop, target, or other hit. The website list uses the same check."""
    from app import alerts, mailer
    from app.main import _alert_quotes
    doc = alerts.load_rules()
    if not doc.get("rules"):
        return []
    out = alerts.check(_alert_quotes(doc["rules"]))
    rings = out.get("rings") or []
    if rings:
        mailer.send_alerts(rings)
    return rings


def tick():
    from app import mailer, report_store, scan as scan_mod
    running, _pids = scan_mod.scan_running()
    report = report_store.latest_report() or {}
    start_at, email_by = schedule()
    choice = decide(None, load_state(), running, report.get("run_date"), start_at, email_by)
    if choice["start"]:
        scan_mod.start_scan(False)
    if choice["send"]:
        result = mailer.send_report(report)
        choice["state"]["mail_ok"] = bool(result.get("ok"))
        choice["state"]["mail_error"] = None if result.get("ok") else result.get("error")
        if result.get("ok"):
            choice["state"]["emailed"] = True
    today = ist_now().date().isoformat()
    if (
        choice["state"].get("started")
        and not choice["state"].get("alerts_synced")
        and not running
        and report.get("run_date") == today
    ):
        _arm_alerts(report)
        choice["state"]["alerts_synced"] = True
    n = ist_now()
    if n.weekday() < 5 and email_by <= n.time() <= WATCH_UNTIL:
        try:
            _watch_alerts()
        except Exception:
            pass
    if choice["start"] or choice["send"] or choice["state"] != load_state():
        save_state(choice["state"])
    return choice


def loop():
    while True:
        try:
            tick()
        except Exception:
            pass
        time.sleep(60)
