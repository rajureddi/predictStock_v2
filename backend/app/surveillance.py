"""Exchange surveillance veto (ASM / GSM / trade-to-trade) and earnings-date
flag for stage-2 candidates.

NSE puts volatile small caps under Additional / Graded Surveillance (100%
margin, T2T settlement, 5% circuits). A swing trader never holds these for
five days, so they are a hard veto BEFORE the expensive stage-2 evaluation.

* ASM / GSM lists: NSE's `api/reportASM` and `api/reportGSM` (JSON, needs a
  cookie session). Best effort: cached to data/surveillance_cache.json, and a
  stale cache is used when the fetch fails. No data at all => no veto.
* T2T: the universe listing's NSE `series` — "BE" / "BZ" are trade-to-trade.
* Earnings: yfinance `Ticker.calendar` for the shortlisted pool, cached daily
  (data/earnings_cache.json). A results date inside [run_date, target_date]
  is a coin-flip gap event: skipped when enough clean picks exist, otherwise
  kept but flagged `earnings_in_window`.

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
T2T_SERIES = {"BE", "BZ"}
NSE_HOME = "https://www.nseindia.com"
NSE_ENDPOINTS = {"asm": f"{NSE_HOME}/api/reportASM", "gsm": f"{NSE_HOME}/api/reportGSM"}
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{NSE_HOME}/reports/surveillance",
}
STALE_DAYS = 10  # beyond this a cached list is too old to veto on


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


# ---------------------------------------------------------------- ASM / GSM
def fetch_nse_lists(timeout=12, log=print):
    """{asm: [symbols], gsm: [symbols]} from NSE, or None if blocked."""
    try:
        import requests
    except ImportError:
        log("[surveillance] requests not installed — skipping NSE fetch"); return None
    try:
        s = requests.Session(); s.headers.update(NSE_HEADERS)
        s.get(NSE_HOME, timeout=timeout)  # cookie bootstrap
        out = {}
        for key, url in NSE_ENDPOINTS.items():
            r = s.get(url, timeout=timeout)
            r.raise_for_status()
            out[key] = extract_symbols(r.json())
        if not out.get("asm") and not out.get("gsm"):
            return None
        return out
    except Exception as e:
        log(f"[surveillance] NSE fetch failed: {e}")
        return None


def get_surveillance_lists(log=print, max_age_days=1):
    """Cached ASM/GSM symbol sets. Returns dict(asm=set, gsm=set, fetched=str|None, stale=bool)."""
    cache = _load(CACHE_F)
    fetched = cache.get("fetched")
    fresh = fetched and fetched >= (date.today() - timedelta(days=max_age_days)).isoformat()
    if not fresh:
        live = fetch_nse_lists(log=log)
        if live:
            cache = dict(fetched=date.today().isoformat(), asm=live.get("asm", []), gsm=live.get("gsm", []))
            _save(CACHE_F, cache); fetched = cache["fetched"]
            log(f"[surveillance] NSE lists: ASM {len(cache['asm'])} · GSM {len(cache['gsm'])}")
        elif fetched:
            log(f"[surveillance] using stale cache from {fetched}")
    stale = bool(fetched) and fetched < (date.today() - timedelta(days=STALE_DAYS)).isoformat()
    if stale or not fetched:
        return dict(asm=set(), gsm=set(), fetched=fetched, stale=True)
    return dict(asm=set(cache.get("asm", [])), gsm=set(cache.get("gsm", [])), fetched=fetched, stale=False)


def surveillance_flags(symbol, exchange, series=None, lists=None):
    """List of flags for one listing: 'ASM', 'GSM', 'T2T'. Empty = clean."""
    flags = []
    if exchange == "NSE":
        sym = (symbol or "").upper()
        if lists:
            if sym in lists.get("asm", ()): flags.append("ASM")
            if sym in lists.get("gsm", ()): flags.append("GSM")
        if (series or "").upper() in T2T_SERIES: flags.append("T2T")
    return flags


def apply_surveillance_veto(candidates, series_map=None, lists=None, log=print):
    """Hard veto. `series_map` = {(symbol, exchange): series}. Returns
    (clean, vetoed) where vetoed rows are compact report entries."""
    try:
        if lists is None: lists = get_surveillance_lists(log=log)
    except Exception as e:
        log(f"[surveillance] lists unavailable: {e}"); lists = dict(asm=set(), gsm=set())
    series_map = series_map or {}
    clean, vetoed = [], []
    for c in candidates:
        series = c.get("series") or series_map.get((c.get("symbol"), c.get("exchange")))
        flags = surveillance_flags(c.get("symbol"), c.get("exchange"), series, lists)
        if flags:
            reason = " + ".join({"ASM": "Additional Surveillance (ASM)", "GSM": "Graded Surveillance (GSM)",
                                 "T2T": f"Trade-to-trade series {series}"}[f] for f in flags)
            vetoed.append(dict(symbol=c.get("symbol"), name=c.get("name"), exchange=c.get("exchange"),
                               current_price=c.get("current_price"), trader_score=c.get("trader_score"),
                               flags=flags, reason=reason))
            log(f"[surveillance] VETO {c.get('symbol')}: {reason}")
        else:
            clean.append(c)
    return clean, vetoed


# ---------------------------------------------------------------- earnings
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
    """{yahoo: [iso dates]} cached for the day. Threaded, fail-safe."""
    cache = _load(EARN_CACHE_F)
    today = date.today().isoformat()
    out, todo = {}, []
    for y in yahoo_list:
        c = cache.get(y)
        if c and c.get("fetched") == today: out[y] = c.get("dates", [])
        else: todo.append(y)
    if todo:
        log(f"[earnings] fetching calendars for {len(todo)} symbols ({len(out)} cached)")
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(_fetch_calendar, y): y for y in todo}
            for fut, y in futs.items():
                try: dates = fut.result(timeout=4)
                except Exception: dates = []
                out[y] = dates; cache[y] = dict(fetched=today, dates=dates)
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
