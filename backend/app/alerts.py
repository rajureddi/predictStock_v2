"""NSE/BSE price alerts for MarketMind picks.

Adapted from trader/alerts.py: a rule rings once, then stays quiet until it is
reset. The clock is India Standard Time and the session is the NSE cash market
(09:15–15:30 IST, weekdays). Quotes come from the app's live-quote path, which
is the latest official close, not a broker tape. An alert is information, not
an order.
"""
import json
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "data" / "alerts_rules.json"
STATE_PATH = ROOT / "data" / "alerts_state.json"
IST = ZoneInfo("Asia/Kolkata")
PRICE_BELOW = {"stop", "below", "reversal"}
PRICE_ABOVE = {"target", "target2", "above"}
NO_QUOTE = {"cutoff"}


def ist_now(now=None):
    if now is None:
        return datetime.now(IST)
    if now.tzinfo is None:
        return now.replace(tzinfo=IST)
    return now.astimezone(IST)


def session_status(now=None):
    n = ist_now(now)
    t = n.time()
    open_ = n.weekday() < 5 and time(9, 15) <= t <= time(15, 30)
    return {
        "ist": n.strftime("%Y-%m-%d %H:%M IST"),
        "date": n.date().isoformat(),
        "weekday": n.strftime("%A"),
        "open": open_,
        "reason": "NSE cash session 09:15–15:30 IST" if open_ else "NSE cash session closed",
    }


def _read(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")


def load_rules():
    doc = _read(RULES_PATH, {"rules": []})
    if not isinstance(doc, dict):
        doc = {"rules": []}
    doc.setdefault("rules", [])
    return doc


def load_state():
    doc = _read(STATE_PATH, {"rung": {}})
    if not isinstance(doc, dict):
        doc = {"rung": {}}
    doc.setdefault("rung", {})
    return doc


def _hhmm(value):
    try:
        h, m = str(value).split(":")
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return time(h, m)
    except Exception:
        return None
    return None


def _hit(rule, price, now):
    kind = rule.get("type")
    if kind in NO_QUOTE:
        at = _hhmm(rule.get("at") or "15:20")
        n = ist_now(now)
        return bool(at) and n.weekday() < 5 and n.time() >= at
    if price is None:
        return False
    if kind in PRICE_BELOW:
        level = rule.get("price")
        return level is not None and price <= float(level)
    if kind in PRICE_ABOVE:
        level = rule.get("price")
        return level is not None and price >= float(level)
    if kind in ("massive_selling", "pct_move"):
        entry = rule.get("entry_price") or rule.get("ref")
        pct = rule.get("pct")
        if entry in (None, 0) or pct is None:
            return False
        move = (price - float(entry)) / float(entry) * 100
        direction = rule.get("direction") or ("down" if kind == "massive_selling" else "any")
        if direction == "down":
            return move <= -abs(float(pct))
        if direction == "up":
            return move >= abs(float(pct))
        return abs(move) >= abs(float(pct))
    return False


def _message(rule, price):
    note = rule.get("note")
    if note:
        base = note
    else:
        base = f"{rule.get('symbol') or 'MARKET'} {rule.get('type')}"
    if price is None:
        return base
    return f"{base} · last close ₹{price:,.2f}"


def _already_rung(rule, state, now):
    """Price alerts stay quiet after one hit. The 15:20 review rings once per weekday."""
    stamp = (state.get("rung") or {}).get(rule.get("id"))
    if not stamp:
        return False
    if rule.get("type") not in NO_QUOTE:
        return True
    try:
        prev = datetime.fromisoformat(stamp)
        if prev.tzinfo is None:
            prev = prev.replace(tzinfo=IST)
        return prev.astimezone(IST).date() == ist_now(now).date()
    except Exception:
        return True


def evaluate(rules, quotes, state=None, now=None):
    """Return (rings, new_state). quotes is {SYMBOL: price}. A rung rule stays quiet."""
    state = {"rung": dict((state or {}).get("rung") or {})}
    rings = []
    n = ist_now(now)
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        rid = rule.get("id")
        if not rid or _already_rung(rule, state, n):
            continue
        sym = (rule.get("symbol") or "").upper()
        price = None if rule.get("type") in NO_QUOTE else quotes.get(sym)
        if rule.get("type") not in NO_QUOTE and price is None:
            continue
        if not _hit(rule, price, n):
            continue
        state["rung"][rid] = n.isoformat()
        rings.append({
            "id": rid,
            "symbol": sym or "MARKET",
            "exchange": rule.get("exchange"),
            "type": rule.get("type"),
            "price": price,
            "message": _message(rule, price),
            "at": n.isoformat(),
        })
    return rings, state


def snapshot(quotes=None):
    doc = load_rules()
    state = load_state()
    status = session_status()
    rows = []
    for rule in doc["rules"]:
        row = dict(rule)
        sym = (rule.get("symbol") or "").upper()
        row["last"] = None if quotes is None else quotes.get(sym)
        row["rung"] = _already_rung(rule, state, ist_now())
        rows.append(row)
    return {"market": status, "rules": rows, "rung": state["rung"]}


def check(quotes, now=None):
    doc = load_rules()
    state = load_state()
    rings, state = evaluate(doc["rules"], quotes, state, now=now)
    _write(STATE_PATH, state)
    out = snapshot(quotes)
    out["rings"] = rings
    return out


def reset(rule_id=None):
    state = load_state()
    if rule_id:
        state["rung"].pop(rule_id, None)
    else:
        state["rung"] = {}
    _write(STATE_PATH, state)
    return snapshot()


def add_rule(rule):
    doc = load_rules()
    rule = dict(rule)
    rule.setdefault("enabled", True)
    rule.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    if not rule.get("id"):
        rule["id"] = f"user-{rule.get('symbol','MARKET')}-{rule.get('type')}-{int(datetime.now().timestamp())}"
    doc["rules"] = [r for r in doc["rules"] if r.get("id") != rule["id"]] + [rule]
    _write(RULES_PATH, doc)
    state = load_state()
    state["rung"].pop(rule["id"], None)
    _write(STATE_PATH, state)
    return snapshot()


def set_enabled(rule_id, enabled):
    doc = load_rules()
    for rule in doc["rules"]:
        if rule.get("id") == rule_id:
            rule["enabled"] = bool(enabled)
    _write(RULES_PATH, doc)
    return snapshot()


def sync_from_picks(picks):
    """Replace pick-derived rules with stop, target, target 2, a 2.5% drop and a 1.5% reversal.
    Keeps rules the user added by hand. Clears rung marks for the replaced ids."""
    doc = load_rules()
    kept = [r for r in doc["rules"] if not str(r.get("id", "")).startswith(("pick-", "system-cutoff"))]
    now = datetime.now(timezone.utc).isoformat()
    fresh = [{
        "id": "system-cutoff-1520",
        "symbol": "MARKET",
        "type": "cutoff",
        "at": "15:20",
        "note": "Review open positions 10 minutes before the 15:30 IST close",
        "enabled": True,
        "created_at": now,
    }]
    for p in picks or []:
        sym = p.get("symbol")
        if not sym:
            continue
        ex = p.get("exchange") or "NSE"
        entry = p.get("current_price")
        base = {"symbol": sym, "exchange": ex, "entry_price": entry, "enabled": True, "created_at": now}
        if p.get("stop_loss"):
            fresh.append({**base, "id": f"pick-{sym}-stop", "type": "stop", "price": p["stop_loss"],
                          "note": f"{sym} stop-loss at ₹{p['stop_loss']:,.2f}"})
        if p.get("target"):
            fresh.append({**base, "id": f"pick-{sym}-target1", "type": "target", "price": p["target"],
                          "note": f"{sym} target 1 at ₹{p['target']:,.2f}"})
        if p.get("target2"):
            fresh.append({**base, "id": f"pick-{sym}-target2", "type": "target2", "price": p["target2"],
                          "note": f"{sym} target 2 at ₹{p['target2']:,.2f}"})
        if entry:
            fresh.append({**base, "id": f"pick-{sym}-dump", "type": "massive_selling", "pct": 2.5,
                          "direction": "down", "note": f"{sym} fell 2.5% from the scan price"})
            fresh.append({**base, "id": f"pick-{sym}-reversal", "type": "reversal",
                          "price": round(float(entry) * 0.985, 2),
                          "note": f"{sym} dropped 1.5% below the scan price"})
    doc["rules"] = kept + fresh
    _write(RULES_PATH, doc)
    state = load_state()
    for rule in fresh:
        state["rung"].pop(rule["id"], None)
    _write(STATE_PATH, state)
    return snapshot()
