"""Sector labels (yfinance `info.sector`, 90-day cache) and the sector
concentration cap: three pharma names are one bet, not three.

Fail-safe: a pick with no sector label is never capped.
"""
import json, warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
CACHE_F = ROOT / "data" / "sector_cache.json"
CACHE_DAYS = 90
MAX_PER_SECTOR = 2


def _load():
    try: return json.loads(CACHE_F.read_text(encoding="utf-8"))
    except Exception: return {}


def _save(c):
    try:
        CACHE_F.parent.mkdir(parents=True, exist_ok=True)
        CACHE_F.write_text(json.dumps(c), encoding="utf-8")
    except Exception: pass


def _fetch_one(yahoo):
    import yfinance as yf
    info = yf.Ticker(yahoo).info or {}
    sec = info.get("sector"); ind = info.get("industry")
    return dict(sector=str(sec).strip() if sec else None, industry=str(ind).strip() if ind else None)


def fetch_sectors(yahoo_list, log=print):
    """{yahoo: {sector, industry}} — cached 90 days, threaded, fail-safe."""
    cache = _load()
    cutoff = (date.today() - timedelta(days=CACHE_DAYS)).isoformat()
    out, todo = {}, []
    for y in yahoo_list:
        c = cache.get(y)
        if c and c.get("fetched", "") >= cutoff: out[y] = c.get("data") or {}
        else: todo.append(y)
    if todo:
        log(f"[sectors] fetching {len(todo)} symbols ({len(out)} cached)")
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(_fetch_one, y): y for y in todo}
            for fut, y in futs.items():
                try: data = fut.result(timeout=4)
                except Exception: data = {}
                out[y] = data; cache[y] = dict(fetched=date.today().isoformat(), data=data)
        _save(cache)
    return out


def attach_sectors(picks, log=print):
    """Sets `sector` / `industry` on picks that carry a `yahoo` key. Never raises."""
    try:
        res = fetch_sectors([p["yahoo"] for p in picks if p.get("yahoo")], log=log)
        for p in picks:
            d = res.get(p.get("yahoo")) or {}
            p["sector"] = d.get("sector"); p["industry"] = d.get("industry")
    except Exception as e:
        log(f"[sectors] attach failed: {e}")
        for p in picks:
            p.setdefault("sector", None); p.setdefault("industry", None)
    return picks


def apply_sector_cap(ranked, want=7, max_per_sector=MAX_PER_SECTOR):
    """Walk the ranked list keeping at most `max_per_sector` per sector.
    Capped picks fill remaining slots only if the pool is shorter than
    `want`. Returns (pool, capped) — capped rows are compact report entries."""
    counts, pool, capped = {}, [], []
    for p in ranked:
        sec = p.get("sector")
        if sec and counts.get(sec, 0) >= max_per_sector:
            capped.append(p)
        else:
            pool.append(p)
            if sec: counts[sec] = counts.get(sec, 0) + 1
    while len(pool) < want and capped:
        p = capped.pop(0); p["sector_cap_filled"] = True; pool.append(p)
    pool.sort(key=lambda p: ranked.index(p))
    capped_out = [dict(symbol=p["symbol"], name=p.get("name"), exchange=p.get("exchange"),
                       sector=p.get("sector"), current_price=p.get("current_price"),
                       predicted_return_pct=p.get("predicted_return_pct")) for p in capped]
    return pool, capped_out
