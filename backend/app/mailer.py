"""Email this week's picks. SMTP settings stay in data/mail_config.json and are
never returned in full. Gmail works with an app password on smtp.gmail.com:587.
"""
import json
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data" / "mail_config.json"
MASK = "••••••••"


def _blank():
    return {
        "to": "",
        "from_addr": "",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "scan_start": "07:00",
        "email_by": "09:15",
    }


def load_config():
    cfg = _blank()
    try:
        if CONFIG_PATH.exists():
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update({k: saved.get(k, cfg[k]) for k in cfg})
    except Exception:
        pass
    return cfg


def clock(value):
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(value or ""))
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def parse_recipients(value):
    found = []
    bad = []
    for chunk in re.split(r"[\s,;]+", str(value or "").strip()):
        if not chunk:
            continue
        if "@" not in chunk or chunk.startswith("@") or chunk.endswith("@"):
            bad.append(chunk)
            continue
        if chunk not in found:
            found.append(chunk)
    return found, bad


def recipients(cfg=None):
    cfg = load_config() if cfg is None else cfg
    found, _bad = parse_recipients(cfg.get("to"))
    return found


def public_config():
    cfg = load_config()
    found, _bad = parse_recipients(cfg.get("to"))
    return {
        "to": ", ".join(found),
        "recipients": found,
        "from_addr": cfg["from_addr"],
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "smtp_user": cfg["smtp_user"],
        "has_password": bool(cfg["smtp_password"]),
        "scan_start": clock(cfg.get("scan_start")) or "07:00",
        "email_by": clock(cfg.get("email_by")) or "09:15",
    }


def save_config(updates):
    cfg = load_config()
    updates = updates or {}
    if "to" in updates and updates["to"] is not None:
        found, bad = parse_recipients(updates["to"])
        if bad:
            return {"ok": False, "error": "Check this address: " + ", ".join(bad)}
        cfg["to"] = ", ".join(found)
    for key in ("from_addr", "smtp_host", "smtp_user"):
        if key in updates and updates[key] is not None:
            cfg[key] = str(updates[key]).strip()
    if "scan_start" in updates and updates["scan_start"] is not None:
        start = clock(updates["scan_start"])
        if not start:
            return {"ok": False, "error": "Scan start must be a time like 07:00."}
        cfg["scan_start"] = start
    if "email_by" in updates and updates["email_by"] is not None:
        by = clock(updates["email_by"])
        if not by:
            return {"ok": False, "error": "Email-by must be a time like 09:15."}
        cfg["email_by"] = by
    if (clock(cfg.get("scan_start")) or "07:00") >= (clock(cfg.get("email_by")) or "09:15"):
        return {"ok": False, "error": "The email time has to be later than the scan start."}
    if updates.get("smtp_port"):
        cfg["smtp_port"] = int(updates["smtp_port"])
    password = updates.get("smtp_password")
    if password and MASK not in str(password):
        cfg["smtp_password"] = str(password)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    out = public_config()
    out["ok"] = True
    return out


PORTFOLIO_PATH = ROOT / "data" / "portfolio.json"


def load_portfolio():
    try:
        if PORTFOLIO_PATH.exists():
            doc = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
            rows = doc.get("holdings") if isinstance(doc, dict) else doc
            if isinstance(rows, list):
                return [r for r in rows if isinstance(r, dict) and r.get("symbol")]
    except Exception:
        pass
    return []


def save_portfolio(rows):
    clean = []
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("symbol"):
            continue
        def _num(key):
            try:
                value = row.get(key)
                return None if value in (None, "") else float(value)
            except (TypeError, ValueError):
                return None
        clean.append({
            "symbol": str(row["symbol"]).upper().strip(),
            "exchange": str(row.get("exchange") or "NSE"),
            "name": str(row.get("name") or ""),
            "shares": _num("shares") or 0,
            "buy": _num("buy") or 0,
            "added": str(row.get("added") or ""),
            "predicted": _num("predicted"),
            "target": _num("target"),
            "stop": _num("stop"),
        })
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_PATH.write_text(json.dumps({"holdings": clean}, indent=1), encoding="utf-8")
    return {"holdings": clean}


def _inr(value):
    if value is None:
        return "—"
    return f"₹{float(value):,.2f}"


def _money(value):
    """Rupee amount as an HTML entity so mail clients do not scramble the sign."""
    if value is None:
        return "&mdash;"
    n = float(value)
    sign = "-" if n < 0 else ""
    return f"{sign}&#8377;{abs(n):,.2f}"


def _esc(value):
    return ("" if value is None else str(value)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pct(value):
    if value is None:
        return "—"
    return f"{float(value):+.2f}%"


def _tone(value):
    if value is None:
        return "#5C6B82"
    return "#0E7A4B" if float(value) >= 0 else "#B42318"


def report_text(report, holdings=None):
    report = report or {}
    lines = [
        "MarketMind Pro — today's predictions",
        f"Scanned {report.get('run_date') or '—'}  →  target {report.get('target_date') or '—'}",
        "Analysis, not an order. Prices are the scan close, not a broker fill.",
        "",
        "Today's predictions",
    ]
    picks = report.get("picks") or []
    if not picks:
        lines.append("No picks were published for this scan.")
    for p in picks:
        lines.append(
            f"{p.get('symbol')} ({p.get('exchange') or 'NSE'})  {p.get('name') or ''}".rstrip()
        )
        lines.append(
            f"  scan {_inr(p.get('current_price'))}   predicted {_inr(p.get('predicted_price'))}"
            f"   stop {_inr(p.get('stop_loss'))}   target {_inr(p.get('target'))}"
        )
        reasons = p.get("reasons") or []
        if reasons:
            lines.append("  " + "; ".join(str(r) for r in reasons[:2]))
        lines.append("")
    lines.append("Portfolio")
    holdings = holdings if holdings is not None else load_portfolio()
    if not holdings:
        lines.append("No holdings saved on this computer yet.")
    for h in holdings:
        lines.append(f"{h.get('symbol')}  {float(h.get('shares') or 0):g} sh @ {_inr(h.get('buy'))}")
    return "\n".join(lines).strip() + "\n"


def _stat(label, value, color="#102033"):
    return (
        f'<td style="padding:10px 8px;border-top:1px solid #EEF1F5;" valign="top">'
        f'<div style="font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:#7B8798;">{label}</div>'
        f'<div style="margin-top:3px;font-size:15px;font-weight:650;color:{color};">{value}</div>'
        f"</td>"
    )


def report_html(report, holdings=None, quotes=None):
    report = report or {}
    quotes = quotes or {}
    holdings = holdings if holdings is not None else load_portfolio()
    picks = report.get("picks") or []
    by_symbol = {p.get("symbol"): p for p in picks if p.get("symbol")}
    run = _esc(report.get("run_date") or "—")
    target = _esc(report.get("target_date") or "—")

    cards = []
    if not picks:
        cards.append('<tr><td style="padding:18px 22px;color:#5C6B82;font-size:14px;">No picks were published for this scan.</td></tr>')
    for i, p in enumerate(picks, 1):
        ret = p.get("predicted_return_pct")
        reasons = [str(r) for r in (p.get("reasons") or [])[:2]]
        reason = " &middot; ".join(_esc(r) for r in reasons)
        setup = _esc(p.get("setup_type") or p.get("sector") or "")
        cards.append(f'''
        <tr><td style="padding:0 0 12px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid #E6EBF1;border-radius:14px;">
            <tr>
              <td style="padding:16px 18px 8px;">
                <div style="font-size:12px;color:#8A94A6;letter-spacing:.08em;">{i:02d} &middot; {_esc(p.get("exchange") or "NSE")}{(" &middot; " + setup) if setup else ""}</div>
                <div style="margin-top:4px;font-size:18px;font-weight:700;color:#102033;">{_esc(p.get("symbol"))}</div>
                <div style="font-size:13px;color:#5C6B82;">{_esc(p.get("name") or "")}</div>
              </td>
              <td align="right" style="padding:16px 18px 8px;font-size:20px;font-weight:700;color:{_tone(ret)};">{_esc(_pct(ret))}</td>
            </tr>
            <tr><td colspan="2" style="padding:0 10px 14px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  {_stat("Scan", _money(p.get("current_price")))}
                  {_stat("Predicted", _money(p.get("predicted_price")), "#C2410C")}
                  {_stat("Stop", _money(p.get("stop_loss")), "#B42318")}
                  {_stat("Target", _money(p.get("target")), "#0E7A4B")}
                </tr>
              </table>
              {f'<div style="padding:0 8px 4px;font-size:12px;line-height:1.45;color:#5C6B82;">{reason}</div>' if reason else ""}
            </td></tr>
          </table>
        </td></tr>''')

    invested = value = 0.0
    have_value = False
    rows = []
    for h in holdings:
        sym = str(h.get("symbol") or "").upper()
        shares = float(h.get("shares") or 0)
        buy = float(h.get("buy") or 0)
        last = quotes.get(sym)
        if last is None and sym in by_symbol and by_symbol[sym].get("current_price") is not None:
            last = float(by_symbol[sym]["current_price"])
        cost = shares * buy
        invested += cost
        worth = shares * float(last) if last is not None else None
        if worth is not None:
            value += worth
            have_value = True
        pnl = (worth - cost) if worth is not None else None
        pnl_pct = (pnl / cost * 100) if pnl is not None and cost else None
        rows.append(f'''
          <tr>
            <td style="padding:12px 8px;border-top:1px solid #EEF1F5;">
              <div style="font-weight:700;color:#102033;">{_esc(sym)}</div>
              <div style="font-size:12px;color:#7B8798;">{_esc(h.get("name") or "")}</div>
            </td>
            <td style="padding:12px 8px;border-top:1px solid #EEF1F5;color:#102033;">{shares:g}</td>
            <td style="padding:12px 8px;border-top:1px solid #EEF1F5;color:#102033;">{_money(buy)}</td>
            <td style="padding:12px 8px;border-top:1px solid #EEF1F5;color:#102033;">{_money(last)}</td>
            <td align="right" style="padding:12px 8px;border-top:1px solid #EEF1F5;font-weight:700;color:{_tone(pnl)};">{_money(pnl)}<div style="font-size:12px;font-weight:600;">{_esc(_pct(pnl_pct))}</div></td>
          </tr>''')

    if not rows:
        portfolio = '<tr><td style="padding:8px 4px 0;color:#5C6B82;font-size:14px;">No holdings yet. Add stocks on the Portfolio page and they will be included in the next mail.</td></tr>'
    else:
        total_pnl = (value - invested) if have_value else None
        total_pct = (total_pnl / invested * 100) if total_pnl is not None and invested else None
        portfolio = f'''
        <tr><td style="padding:0 0 10px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#102033;border-radius:14px;">
            <tr>
              <td style="padding:14px 16px;color:#D5DDE8;font-size:12px;letter-spacing:.06em;text-transform:uppercase;">Invested</td>
              <td style="padding:14px 16px;color:#D5DDE8;font-size:12px;letter-spacing:.06em;text-transform:uppercase;">Value</td>
              <td align="right" style="padding:14px 16px;color:#D5DDE8;font-size:12px;letter-spacing:.06em;text-transform:uppercase;">P&amp;L</td>
            </tr>
            <tr>
              <td style="padding:0 16px 16px;color:#FFFFFF;font-size:18px;font-weight:700;">{_money(invested)}</td>
              <td style="padding:0 16px 16px;color:#FFFFFF;font-size:18px;font-weight:700;">{_money(value if have_value else None)}</td>
              <td align="right" style="padding:0 16px 16px;color:{'#8EEDC7' if (total_pnl or 0) >= 0 else '#FFB4AB'};font-size:18px;font-weight:700;">{_money(total_pnl)}<div style="font-size:12px;">{_esc(_pct(total_pct))}</div></td>
            </tr>
          </table>
        </td></tr>
        <tr><td>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid #E6EBF1;border-radius:14px;">
            <tr>
              <td style="padding:12px 8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8A94A6;">Stock</td>
              <td style="padding:12px 8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8A94A6;">Shares</td>
              <td style="padding:12px 8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8A94A6;">Buy</td>
              <td style="padding:12px 8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8A94A6;">Last</td>
              <td align="right" style="padding:12px 8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8A94A6;">P&amp;L</td>
            </tr>
            {''.join(rows)}
          </table>
        </td></tr>'''

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F3F5F8;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F3F5F8;">
    <tr><td align="center" style="padding:28px 12px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:640px;max-width:640px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
        <tr><td style="padding:0 4px 18px;">
          <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#C2410C;font-weight:700;">MarketMind Pro</div>
          <div style="margin-top:6px;font-size:28px;line-height:1.15;font-weight:700;color:#102033;">Today's predictions</div>
          <div style="margin-top:6px;font-size:14px;color:#5C6B82;">Scanned {run} &nbsp;&rarr;&nbsp; target {target}</div>
        </td></tr>
        <tr><td style="height:3px;background:#FF5E1A;border-radius:3px;font-size:0;line-height:0;">&nbsp;</td></tr>
        <tr><td style="padding:18px 4px 8px;font-size:13px;line-height:1.5;color:#5C6B82;">Analysis, not an order. Prices are the latest close, not a broker fill.</td></tr>
        {''.join(cards)}
        <tr><td style="padding:18px 4px 10px;font-size:22px;font-weight:700;color:#102033;">Portfolio</td></tr>
        {portfolio}
        <tr><td style="padding:18px 4px 0;font-size:12px;line-height:1.5;color:#8A94A6;">MarketMind Pro research note. This is not investment advice and it does not place a trade.</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>'''


def _connected_html():
    return '''<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#F3F5F8;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 12px;">
        <table role="presentation" width="520" cellpadding="0" cellspacing="0" style="width:520px;max-width:520px;background:#FFFFFF;border-radius:16px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
          <tr><td style="height:4px;background:#FF5E1A;border-radius:16px 16px 0 0;font-size:0;">&nbsp;</td></tr>
          <tr><td style="padding:28px 28px 8px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#C2410C;font-weight:700;">MarketMind Pro</td></tr>
          <tr><td style="padding:0 28px 8px;font-size:24px;font-weight:700;color:#102033;">Mail is connected</td></tr>
          <tr><td style="padding:0 28px 28px;font-size:14px;line-height:1.5;color:#5C6B82;">The next weekday report will arrive in this format, with that morning’s predictions and your portfolio. Stop and target hits are mailed on their own during the session.</td></tr>
        </table>
      </td></tr></table>
    </body></html>'''


ALERT_LABELS = {
    "stop": ("Stop hit", "#B42318"),
    "below": ("Price below the level", "#B42318"),
    "reversal": ("Reversal", "#B42318"),
    "massive_selling": ("Heavy selling", "#B42318"),
    "target": ("Target hit", "#0E7A4B"),
    "target2": ("Target 2 hit", "#0E7A4B"),
    "above": ("Price above the level", "#0E7A4B"),
    "pct_move": ("Move alert", "#C2410C"),
    "cutoff": ("Close review", "#B45309"),
}


def alert_text(rings):
    lines = ["MarketMind Pro — alert", "A level was reached. This is information, not an order.", ""]
    for ring in rings or []:
        label, _color = ALERT_LABELS.get(ring.get("type"), (ring.get("type") or "Alert", "#102033"))
        lines.append(f"{ring.get('symbol') or 'MARKET'}  {label}")
        if ring.get("message"):
            lines.append(f"  {ring['message']}")
        if ring.get("price") is not None:
            lines.append(f"  last {_inr(ring.get('price'))}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def alert_html(rings):
    cards = []
    for ring in rings or []:
        label, color = ALERT_LABELS.get(ring.get("type"), ("Alert", "#102033"))
        price = _money(ring.get("price")) if ring.get("price") is not None else ""
        cards.append(f'''
        <tr><td style="padding:0 0 12px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid #E6EBF1;border-radius:14px;border-left:4px solid {color};">
            <tr><td style="padding:16px 18px;">
              <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:{color};">{_esc(label)}</div>
              <div style="margin-top:4px;font-size:20px;font-weight:700;color:#102033;">{_esc(ring.get("symbol") or "MARKET")}</div>
              <div style="margin-top:6px;font-size:14px;line-height:1.45;color:#5C6B82;">{_esc(ring.get("message") or "")}</div>
              {f'<div style="margin-top:8px;font-size:16px;font-weight:700;color:#102033;">Last {price}</div>' if price else ""}
            </td></tr>
          </table>
        </td></tr>''')
    if not cards:
        cards.append('<tr><td style="padding:18px 4px;color:#5C6B82;">No alert details were attached.</td></tr>')
    count = len(rings or [])
    title = "Alert" if count == 1 else f"{count} alerts"
    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F3F5F8;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F3F5F8;">
    <tr><td align="center" style="padding:28px 12px;">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:640px;max-width:640px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
        <tr><td style="padding:0 4px 18px;">
          <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#C2410C;font-weight:700;">MarketMind Pro</div>
          <div style="margin-top:6px;font-size:28px;line-height:1.15;font-weight:700;color:#102033;">{title}</div>
        </td></tr>
        <tr><td style="height:3px;background:#FF5E1A;border-radius:3px;font-size:0;line-height:0;">&nbsp;</td></tr>
        <tr><td style="padding:18px 4px 8px;font-size:13px;line-height:1.5;color:#5C6B82;">A watched level was reached. This note does not place a trade. The same alert is marked on the Alerts page.</td></tr>
        {''.join(cards)}
        <tr><td style="padding:8px 4px 0;font-size:12px;line-height:1.5;color:#8A94A6;">MarketMind Pro alert. Prices are the latest close available to the desk, not a broker fill.</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>'''


def _deliver(subject, text, html):
    cfg = load_config()
    missing = [name for name, key in (("to", "to"), ("SMTP host", "smtp_host"), ("SMTP user", "smtp_user"), ("SMTP password", "smtp_password")) if not cfg.get(key)]
    if missing:
        return {"ok": False, "error": "Set " + ", ".join(missing) + " before sending."}
    to = recipients(cfg)
    if not to:
        return {"ok": False, "error": "Add at least one address under Send to."}
    sender = cfg["from_addr"] or cfg["smtp_user"]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"] or 587), timeout=20) as smtp:
            smtp.ehlo()
            if int(cfg["smtp_port"] or 587) != 465:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(cfg["smtp_user"], cfg["smtp_password"])
            smtp.send_message(msg)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "to": ", ".join(to), "subject": subject}


def alert_subject(rings):
    rings = rings or []
    if len(rings) == 1:
        ring = rings[0]
        label, _color = ALERT_LABELS.get(ring.get("type"), ("Alert", "#102033"))
        symbol = ring.get("symbol") or "MARKET"
        return f"MarketMind Pro — {symbol} {label.lower()}"
    return f"MarketMind Pro — {len(rings)} alerts"


def send_alerts(rings):
    if not rings:
        return {"ok": False, "error": "No alerts to send."}
    return _deliver(alert_subject(rings), alert_text(rings), alert_html(rings))


def send_report(report, test=False):
    subject = "MarketMind Pro — mail connected" if test else f"MarketMind Pro — predictions {report.get('run_date') or ''}".strip()
    holdings = [] if test else load_portfolio()
    quotes = {}
    if holdings:
        try:
            from app.main import get_live_quotes
            hints = {h["symbol"]: h.get("exchange") or "NSE" for h in holdings if h.get("symbol")}
            quotes = get_live_quotes(list(hints), hints) or {}
        except Exception:
            quotes = {}
    text = "MarketMind Pro mail is connected.\n" if test else report_text(report, holdings)
    html = _connected_html() if test else report_html(report, holdings, quotes)
    return _deliver(subject, text, html)
