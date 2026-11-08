"""Exchange surveillance veto (ASM / GSM / ESM / trade-to-trade / circuit locks)
and official NSE + Yahoo corporate event / earnings-date filter for stage-2 candidates.

NSE puts volatile small caps under Additional / Graded / Enhanced Surveillance
(100% margin, T2T settlement, 2-5% circuits). A swing trader never holds these
for five days, so they are a hard veto BEFORE the expensive stage-2 evaluation.

* ASM / GSM / ESM lists: NSE's `api/reportASM`, `api/reportGSM`, `api/reportESM`
  (JSON, needs a cookie session). Cached to data/surveillance_cache.json.
* T2T: the universe listing's NSE `series` — "BE" / "BZ" / "ST" / "SZ" / "SM" / "IT".
* Circuit-lock detector: `has_circuit_lock_risk(df)` flags stocks with recent
  O=H=L=C 4%+ upper/lower circuit lock bars where stop-losses cannot execute.
* Earnings & Board Meetings: merges official NSE `api/event-calendar` (which covers
  NSE mid/small-cap board meetings for financial results under SEBI LODR Reg 29)
  with yfinance `Ticker.calendar` fallback, cached daily in data/earnings_cache.json.

Nothing here may break the pipeline — every public function is fail-safe.
"""
import json, warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
CACHE_F = ROOT / "data" / "surveillance_cache.json"
EARN_CACHE_F = ROOT / "data" / "earnings_cache.json"
T2T_SERIES = {"BE", "BZ", "ST", "SZ", "SM", "IT"}
NSE_HOME = "https://www.nseindia.com"
NSE_ENDPOINTS = {
    "asm": f"{NSE_HOME}/api/reportASM",
    "gsm": f"{NSE_HOME}/api/reportGSM",
    "esm": f"{NSE_HOME}/api/reportESM",
}
NSE_EVENT_CAL_URL = f"{NSE_HOME}/api/event-calendar"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{NSE_HOME}/reports/surveillance",
}
STALE_DAYS = 10  # beyond this a cached list is too old to veto on

_RESULT_KEYWORDS = (
    "result", "financial", "quarterly", "audited", "unaudited",
    "q1", "q2", "q3", "q4", "half year", "annual", "demerger", "buyback",
)


# ---------------------------------------------------------------- helpers
def _load(f):
    try: return json.loads(f.read_text(encoding="utf-8"))
    except Exception: return {}


def _save(f, obj):
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(obj, default=str), encoding="utf-8")
    except Exception:
        pass


def extract_symbols(payload):
    """NSE's surveillance JSON shapes vary (dict of stages, lists of rows).
    Walk the payload and collect every `symbol` value."""
    out = set()
    def walk(x):
        if isinstance(x, dict):
            sym = x.get("symbol") or x.get("SYMBOL")
            if isinstance(sym, str) and sym.strip():
                out.add(sym.strip().upper())
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(payload)
    return sorted(out)


# ---------------------------------------------------------------- ASM / GSM / ESM
def fetch_nse_lists(timeout=12, log=print):
    """{asm: [symbols], gsm: [symbols], esm: [symbols]} from NSE, or None if blocked."""
    try:
        import requests
    except ImportError:
        log("[surveillance] requests not installed — skipping NSE fetch"); return None
    try:
        s = requests.Session(); s.headers.update(NSE_HEADERS)
        s.get(NSE_HOME, timeout=timeout)  # cookie bootstrap
        out = {}
        for key, url in NSE_ENDPOINTS.items():
            try:
                r = s.get(url, timeout=timeout)
                r.raise_for_status()
                out[key] = extract_symbols(r.json())
            except Exception:
                out[key] = []
        if not out.get("asm") and not out.get("gsm") and not out.get("esm"):
            return None
        return out
    except Exception as e:
        log(f"[surveillance] NSE fetch failed: {e}")
        return None


def get_surveillance_lists(log=print, max_age_days=1):
    """Cached ASM/GSM/ESM symbol sets. Returns dict(asm=set, gsm=set, esm=set, fetched=str|None, stale=bool)."""
    cache = _load(CACHE_F)
    fetched = cache.get("fetched")
    fresh = fetched and fetched >= (date.today() - timedelta(days=max_age_days)).isoformat()
    if not fresh:
        live = fetch_nse_lists(log=log)
        if live:
            cache = dict(fetched=date.today().isoformat(), asm=live.get("asm", []), gsm=live.get("gsm", []), esm=live.get("esm", []))
            _save(CACHE_F, cache); fetched = cache["fetched"]
            log(f"[surveillance] NSE lists: ASM {len(cache['asm'])} · GSM {len(cache['gsm'])} · ESM {len(cache['esm'])}")
        elif fetched:
            log(f"[surveillance] using stale cache from {fetched}")
    stale = bool(fetched) and fetched < (date.today() - timedelta(days=STALE_DAYS)).isoformat()
    if stale or not fetched:
        return dict(asm=set(), gsm=set(), esm=set(), fetched=fetched, stale=True)
    return dict(asm=set(cache.get("asm", [])), gsm=set(cache.get("gsm", [])), esm=set(cache.get("esm", [])), fetched=fetched, stale=False)


def surveillance_flags(symbol, exchange, series=None, lists=None):
    """List of flags for one listing: 'ASM', 'GSM', 'ESM', 'T2T'. Empty = clean."""
    flags = []
    if exchange == "NSE":
        sym = (symbol or "").upper()
        if lists:
            if sym in lists.get("asm", ()): flags.append("ASM")
            if sym in lists.get("gsm", ()): flags.append("GSM")
            if sym in lists.get("esm", ()): flags.append("ESM")
        if (series or "").upper() in T2T_SERIES: flags.append("T2T")
    return flags


def has_circuit_lock_risk(df, lookback=20):
    """Detects NSE/BSE 5%/10%/20% circuit-locked operator scrips from OHLCV:
    a bar that gaps >=3.8% from prior close with virtually zero trading range ((High-Low)/Close < 0.15%)."""
    try:
        if df is None or len(df) < 10:
            return False
        tail = df.tail(lookback + 1)
        c = tail["Close"].astype(float)
        h = tail["High"].astype(float)
        l = tail["Low"].astype(float)
        prev_c = c.shift(1)
        rng_pct = ((h - l) / c.replace(0, float("nan"))).iloc[1:]
        ret_abs = ((c / prev_c.replace(0, float("nan"))) - 1.0).abs().iloc[1:]
        locked = (rng_pct < 0.0015) & (ret_abs >= 0.038)
        return bool(int(locked.sum()) >= 1)
    except Exception:
        return False


def apply_surveillance_veto(candidates, series_map=None, lists=None, log=print):
    """Hard veto. `series_map` = {(symbol, exchange): series}. Returns
    (clean, vetoed) where vetoed rows are compact report entries."""
    try:
        if lists is None: lists = get_surveillance_lists(log=log)
    except Exception as e:
        log(f"[surveillance] lists unavailable: {e}"); lists = dict(asm=set(), gsm=set(), esm=set())
    series_map = series_map or {}
    clean, vetoed = [], []
    for c in candidates:
        series = c.get("series") or series_map.get((c.get("symbol"), c.get("exchange")))
        flags = surveillance_flags(c.get("symbol"), c.get("exchange"), series, lists)
        if c.get("circuit_locked"):
            flags = list(flags) + ["CIRCUIT"]
        if flags:
            labels = {
                "ASM": "Additional Surveillance (ASM)",
                "GSM": "Graded Surveillance (GSM)",
                "ESM": "Enhanced Surveillance (ESM)",
                "T2T": f"Trade-to-trade series {series}",
                "CIRCUIT": "Recent circuit-lock trap",
            }
            reason = " + ".join(labels.get(f, f) for f in flags)
            vetoed.append(dict(symbol=c.get("symbol"), name=c.get("name"), exchange=c.get("exchange"),
                               current_price=c.get("current_price"), trader_score=c.get("trader_score"),
                               flags=flags, reason=reason))
            log(f"[surveillance] VETO {c.get('symbol')}: {reason}")
        else:
            clean.append(c)
    return clean, vetoed


# ---------------------------------------------------------------- earnings & NSE event calendar
def _to_date(v):
    if v is None: return None
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    try:
        import pandas as pd
        ts = pd.Timestamp(v)
        return None if pd.isna(ts) else ts.date()
    except Exception:
        return None


def fetch_nse_event_calendar(timeout=10, log=print):
    """Fetches official NSE corporate board-meeting / financial-results calendar
    (`api/event-calendar`) so mid/small-cap Indian earnings dates missing from Yahoo are caught."""
    try:
        import requests
    except ImportError:
        return {}
    try:
        s = requests.Session(); s.headers.update(NSE_HEADERS)
        s.get(NSE_HOME, timeout=timeout)
        r = s.get(NSE_EVENT_CAL_URL, timeout=timeout)
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list):
            return {}
        by_yahoo = {}
        for item in rows:
            if not isinstance(item, dict):
                continue
            sym = (item.get("symbol") or item.get("SYMBOL") or "").strip().upper()
            purpose = f"{item.get('purpose', '')} {item.get('bm_desc', '')}".lower()
            if not sym or not any(k in purpose for k in _RESULT_KEYWORDS):
                continue
            dt_obj = _to_date(item.get("date") or item.get("bm_date"))
            if dt_obj:
                yh = f"{sym}.NS"
                by_yahoo.setdefault(yh, set()).add(dt_obj.isoformat())
        return {k: sorted(v) for k, v in by_yahoo.items()}
    except Exception:
        return {}


def _calendar_dates(cal):
    """Earnings dates from a yfinance calendar (dict or DataFrame)."""
    dates = []
    try:
        if cal is None: return dates
        if hasattr(cal, "to_dict") and not isinstance(cal, dict):  # DataFrame (old yfinance)
            try:
                cal = cal.T.to_dict(orient="list") if "Earnings Date" not in cal.index else {"Earnings Date": list(cal.loc["Earnings Date"].values)}
            except Exception:
                cal = {}
        for k, v in (cal or {}).items():
            if "earnings" not in str(k).lower(): continue
            vals = v if isinstance(v, (list, tuple)) else [v]
            for x in vals:
                d = _to_date(x)
                if d: dates.append(d.isoformat())
    except Exception:
        pass
    return sorted(set(dates))


def _fetch_calendar(yahoo):
    import yfinance as yf
    return _calendar_dates(yf.Ticker(yahoo).calendar)


def fetch_earnings_dates(yahoo_list, log=print):
    """{yahoo: [iso dates]} cached for the day. Merges official NSE corporate event
    calendar with yfinance calendar fallback. Threaded, fail-safe."""
    cache = _load(EARN_CACHE_F)
    today = date.today().isoformat()
    out, todo = {}, []
    for y in yahoo_list:
        c = cache.get(y)
        if c and c.get("fetched") == today: out[y] = c.get("dates", [])
        else: todo.append(y)
    if todo:
        from concurrent.futures import wait as futures_wait
        nse_cal = {}
        if any(str(y).endswith(".NS") for y in todo):
            nse_cal = fetch_nse_event_calendar(timeout=4, log=log)
        log(f"[earnings] fetching calendars for {len(todo)} symbols ({len(out)} cached, {len(nse_cal)} NSE events)")
        ex = ThreadPoolExecutor(max_workers=8)
        try:
            futs = {ex.submit(_fetch_calendar, y): y for y in todo}
            done, _ = futures_wait(list(futs.keys()), timeout=5.0)
            for fut, y in futs.items():
                yf_dates = []
                if fut in done:
                    try:
                        yf_dates = fut.result(timeout=0.1) or []
                    except Exception:
                        yf_dates = []
                merged = sorted(set(yf_dates) | set(nse_cal.get(y, [])))
                out[y] = merged
                cache[y] = dict(fetched=today, dates=merged)
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
        _save(EARN_CACHE_F, cache)
    return out


def earnings_in_window(dates, run_date, target_date):
    """First ISO date in [run_date, target_date], else None."""
    lo, hi = str(run_date), str(target_date)
    for d in sorted(dates or []):
        if lo <= d <= hi: return d
    return None


def apply_earnings_filter(ranked, run_date, target_date, keep=7, dates_by_yahoo=None, log=print):
    """Annotates each pick with `earnings_date` / `earnings_in_window`. Picks
    with results inside the window are dropped from the pool when at least
    `keep` clean picks remain; otherwise they stay (flagged). Returns (pool, skipped)."""
    try:
        if dates_by_yahoo is None:
            dates_by_yahoo = fetch_earnings_dates([p["yahoo"] for p in ranked if p.get("yahoo")], log=log)
    except Exception as e:
        log(f"[earnings] unavailable: {e}"); dates_by_yahoo = {}
    clean, flagged = [], []
    for p in ranked:
        dates = dates_by_yahoo.get(p.get("yahoo"), [])
        hit = earnings_in_window(dates, run_date, target_date)
        p["earnings_date"] = hit or (dates[0] if dates else None)
        p["earnings_in_window"] = bool(hit)
        (flagged if hit else clean).append(p)
    if flagged:
        log(f"[earnings] results inside the window: {[p['symbol'] for p in flagged]}")
    if flagged and len(clean) >= keep:
        return clean, flagged
    return ranked, []
