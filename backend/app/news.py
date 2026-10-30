"""News check for final candidates: Google News RSS headlines (<=14 days),
transparent keyword sentiment, and a hard veto for disaster headlines
(fraud / default / insolvency / SEBI ban or penalty / raid / arrest).

A vetoed candidate is excluded from the final picks when enough clean
candidates remain, and is always listed in the report's "vetoed" section —
visible, never silent. News failures return None and never break the run.
"""
import math, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
MAX_AGE_DAYS = 14
MAX_ITEMS = 6

POSITIVE = ["surge", "jumps", "jump", "rally", "rallies", "profit rises", "profit up",
            "profits rise", "order win", "wins order", "bags order", "bagged", "stake buy",
            "buys stake", "invests", "investment", "upgrade", "upgraded", "record high",
            "approval", "approved", "expansion", "expands", "beats estimates", "beat estimates",
            "pat doubles", "pat up", "profit doubles", "rises", "gains", "soars", "zooms",
            "strong results", "robust", "multibagger", "bonus", "dividend"]
NEGATIVE = ["falls", "fall", "plunge", "plunges", "loss widens", "losses widen", "fraud",
            "default", "sebi", "penalty", "raid", "probe", "investigation", "resignation",
            "resigns", "insolvency", "downgrade", "downgraded", "declines", "drops", "slips",
            "weak results", "misses estimates", "lawsuit", "scam", "arrest"]
VETO = ["fraud", "default", "insolvency", "sebi ban", "sebi bars", "sebi penalty",
        "penalised by sebi", "penalized by sebi", "raid", "arrest", "bankruptcy", "scam"]


def analyse_headlines(headlines):
    """Pure scoring over headline dicts -> {sentiment_score, sentiment_label,
    veto, veto_reason}."""
    pos = neg = 0
    veto, veto_reason = False, None
    for h in headlines:
        t = (h.get("title") or "").lower()
        for w in VETO:
            if w in t:
                veto, veto_reason = True, h.get("title")
                break
        pos += sum(1 for w in POSITIVE if w in t)
        neg += sum(1 for w in NEGATIVE if w in t)
    total = pos + neg
    score = round((pos - neg) / total, 2) if total else 0.0
    label = "Positive" if score >= 0.25 else "Negative" if score <= -0.25 else "Neutral"
    return dict(sentiment_score=score, sentiment_label=label,
                veto=bool(veto), veto_reason=veto_reason)


def fetch_news(name, symbol=None):
    """Google News RSS for '"<name>" share'. Returns news dict or None."""
    q = urllib.parse.quote(f'"{name}" share')
    url = RSS.format(q=q)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            xml = r.read()
        root = ET.fromstring(xml)
    except Exception:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    items = []
    for item in root.iter("item"):
        try:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            src_el = item.find("source")
            source = (src_el.text or "").strip() if src_el is not None and src_el.text else ""
            if title.endswith(f" - {source}") and source:
                title = title[: -len(f" - {source}")].strip()
            dt = parsedate_to_datetime(item.findtext("pubDate"))
            if dt is not None and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt is not None and dt < cutoff:
                continue
            items.append(dict(title=title, source=source, url=link,
                              date=dt.date().isoformat() if dt else None))
        except Exception:
            continue
        if len(items) >= MAX_ITEMS:
            break
    if not items:
        return None
    out = dict(headlines=items)
    out.update(analyse_headlines(items))
    return out


def get_news(pick, log=print):
    """News dict for one candidate (or None). Never raises."""
    try:
        return fetch_news(pick.get("name", ""), pick.get("symbol"))
    except Exception as e:
        log(f"[news] {pick.get('symbol')} failed: {e}")
        return None
