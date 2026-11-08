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
        from concurrent.futures import wait as futures_wait
        log(f"[sectors] fetching {len(todo)} symbols ({len(out)} cached)")
        ex = ThreadPoolExecutor(max_workers=8)
        try:
            futs = {ex.submit(_fetch_one, y): y for y in todo}
            done, _ = futures_wait(list(futs.keys()), timeout=6.0)
            for fut, y in futs.items():
                data = {}
                if fut in done:
                    try:
                        data = fut.result(timeout=0.1) or {}
                    except Exception:
                        data = {}
                out[y] = data
                if data:
                    cache[y] = dict(fetched=date.today().isoformat(), data=data)
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
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


def apply_correlation_cap(ranked, frames_by_key=None, want=7, max_corr=0.70, lookback=60, fill_if_short=False):
    """60-day pairwise daily-return correlation gate (`corr <= 0.70`).
    Prevents hidden thematic concentration (e.g. PSU / Defence / Adani / Tata clusters
    that span multiple Yahoo sectors yet dump together on a single macro headline).
    Returns (pool, corr_capped)."""
    if len(ranked) <= 1:
        return list(ranked), []
    from app import datafeed
    import numpy as np

    ret_cache = {}
    def _rets(p):
        yh = p.get("yahoo") or f"{p.get('symbol')}.NS"
        if yh in ret_cache:
            return ret_cache[yh]
        df = (frames_by_key or {}).get(yh)
        if df is None:
            try:
                df = datafeed.local_history(yh)
            except Exception:
                df = None
        if df is None or "Close" not in df.columns or len(df) < 25:
            ret_cache[yh] = None
            return None
        s = df["Close"].dropna().tail(lookback + 1).pct_change().dropna()
        ret_cache[yh] = s if len(s) >= 20 else None
        return ret_cache[yh]

    pool, corr_capped = [], []
    for p in ranked:
        r_cand = _rets(p)
        too_corr_sym = None
        too_corr_val = 0.0
        if r_cand is not None:
            for existing in pool:
                r_ex = _rets(existing)
                if r_ex is None:
                    continue
                common = r_cand.index.intersection(r_ex.index)
                if len(common) < 20:
                    continue
                a = r_cand.loc[common].to_numpy(dtype=float)
                b = r_ex.loc[common].to_numpy(dtype=float)
                if np.std(a) > 1e-8 and np.std(b) > 1e-8:
                    corr = float(np.corrcoef(a, b)[0, 1])
                    if corr >= max_corr:
                        too_corr_sym = existing.get("symbol")
                        too_corr_val = round(corr, 2)
                        break
        if too_corr_sym:
            p_copy = dict(p)
            p_copy["correlated_with"] = too_corr_sym
            p_copy["correlation"] = too_corr_val
            corr_capped.append(p_copy)
        else:
            pool.append(p)

    if fill_if_short:
        while len(pool) < want and corr_capped:
            p = corr_capped.pop(0)
            p["correlation_cap_filled"] = True
            pool.append(p)
    pool.sort(key=lambda p: next((i for i, r in enumerate(ranked) if r.get("symbol") == p.get("symbol")), 999))
    capped_out = [
        dict(
            symbol=p["symbol"],
            name=p.get("name"),
            exchange=p.get("exchange"),
            sector=p.get("sector"),
            correlated_with=p.get("correlated_with"),
            correlation=p.get("correlation"),
            current_price=p.get("current_price"),
            predicted_return_pct=p.get("predicted_return_pct"),
        )
        for p in corr_capped
    ]
    return pool, capped_out
