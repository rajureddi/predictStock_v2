"""Fundamentals check for stage-2 candidates (yfinance .info, cached).

A fundamentals failure must NEVER break the pipeline: anything that goes
wrong yields None fields and a neutral score. Scoring is transparent and
rule-based (see score_fundamentals) so the report can show exactly why.
"""
import json, warnings
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import date, timedelta
from pathlib import Path
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
CACHE_F = ROOT / "data" / "fundamentals_cache.json"
FIELDS = ["trailingPE", "forwardPE", "returnOnEquity", "debtToEquity",
          "marketCap", "revenueGrowth", "earningsGrowth", "dividendYield"]
CACHE_DAYS = 7
FETCH_TIMEOUT = 45  # seconds per symbol batch wait


def _clean_num(v):
    try:
        f = float(v)
        return f if f == f and abs(f) != float("inf") else None
    except Exception:
        return None


def score_fundamentals(d):
    """(score 0..100, flags) from a dict with keys pe, roe (fraction),
    debt_to_equity, revenue_growth, earnings_growth (fractions)."""
    score, flags = 50.0, []
    roe, de, eg = d.get("roe"), d.get("debt_to_equity"), d.get("earnings_growth")
    rg, pe = d.get("revenue_growth"), d.get("pe")
    if roe is not None:
        if roe > 0.15: score += 12; flags.append(f"Strong ROE {roe * 100:.0f}%")
        elif roe < 0.05: score -= 8; flags.append(f"Weak ROE {roe * 100:.0f}%")
    if de is not None:
        if de < 0.5: score += 8
        elif de > 2: score -= 12; flags.append(f"High debt — D/E {de:.1f}")
    if eg is not None:
        if eg > 0.20: score += 10; flags.append(f"Earnings growth +{eg * 100:.0f}%")
        elif eg < 0: score -= 8; flags.append(f"Earnings fell {eg * 100:.0f}%")
    if rg is not None:
        if rg > 0.15: score += 6; flags.append(f"Revenue growth +{rg * 100:.0f}%")
        elif rg < 0: score -= 6; flags.append(f"Revenue fell {rg * 100:.0f}%")
    if pe is not None:
        if pe < 0: score -= 10; flags.append("Loss-making (negative PE)")
        elif 5 <= pe <= 30: score += 4
        elif pe > 60: score -= 6; flags.append(f"Expensive — PE {pe:.0f}")
    return round(max(0.0, min(100.0, score)), 1), flags


def severe_red_flag(fund):
    """D/E > 3 AND earnings shrinking — the demotion rule."""
    if not fund: return False
    de, eg = fund.get("debt_to_equity"), fund.get("earnings_growth")
    return de is not None and eg is not None and de > 3 and eg < 0


def _fetch_one(yahoo):
    import yfinance as yf
    info = yf.Ticker(yahoo).info or {}
    raw = {k: _clean_num(info.get(k)) for k in FIELDS}
    # Yahoo reports debtToEquity as a PERCENT (46.3 means a 0.46 ratio) —
    # convert to a true ratio or every healthy company looks over-levered.
    de = raw["debtToEquity"] / 100.0 if raw["debtToEquity"] is not None else None
    d = dict(pe=raw["trailingPE"], forward_pe=raw["forwardPE"], roe=raw["returnOnEquity"],
             debt_to_equity=de, market_cap=raw["marketCap"],
             revenue_growth=raw["revenueGrowth"], earnings_growth=raw["earningsGrowth"],
             dividend_yield=raw["dividendYield"])
    if all(v is None for v in d.values()):
        return None
    score, flags = score_fundamentals(d)
    d.update(score=score, flags=flags)
    return d


def _load_cache():
    try:
        return json.loads(CACHE_F.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(c):
    try:
        CACHE_F.parent.mkdir(parents=True, exist_ok=True)
        CACHE_F.write_text(json.dumps(c), encoding="utf-8")
    except Exception:
        pass


def fetch_fundamentals(yahoo_list, log=print):
    """{yahoo: fundamentals dict | None}. Cached 7 days; threaded fetches."""
    cache = _load_cache()
    cutoff = (date.today() - timedelta(days=CACHE_DAYS)).isoformat()
    out, todo = {}, []
    for y in yahoo_list:
        c = cache.get(y)
        if c and c.get("fetched", "") >= cutoff and c.get("data") is not None:
            out[y] = c["data"]
        else:
            todo.append(y)
    if todo:
        log(f"[fundamentals] fetching {len(todo)} symbols ({len(out)} cached)")
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(_fetch_one, y): y for y in todo}
            for fut, y in futs.items():
                try:
                    data = fut.result(timeout=FETCH_TIMEOUT)
                except Exception:
                    data = None
                out[y] = data
                cache[y] = {"fetched": date.today().isoformat(), "data": data}
        _save_cache(cache)
    return out


def attach_fundamentals(picks, log=print):
    """Mutates pick dicts (they carry a 'yahoo' key during stage 2) adding
    'fundamentals' (dict or None). Never raises. Yahoo has no .info for
    most .BO tickers, so a BSE listing with no data falls back to the SAME
    company's NSE ticker (matched by ISIN) when one exists."""
    try:
        res = fetch_fundamentals([p["yahoo"] for p in picks], log=log)
        for p in picks:
            p["fundamentals"] = res.get(p["yahoo"])
        missing = [p for p in picks if p["fundamentals"] is None
                   and p["yahoo"].endswith(".BO") and p.get("isin")]
        if missing:
            try:
                from app import universe as univ_mod
                nse_by_isin = {l["isin"]: l["yahoo"] for l in univ_mod.load_universe()["listings"]
                               if l["exchange"] == "NSE" and l.get("isin")}
                alt = {p["yahoo"]: nse_by_isin[p["isin"]] for p in missing if p["isin"] in nse_by_isin}
                if alt:
                    res2 = fetch_fundamentals(sorted(set(alt.values())), log=log)
                    for p in missing:
                        if alt.get(p["yahoo"]) and res2.get(alt[p["yahoo"]]):
                            p["fundamentals"] = res2[alt[p["yahoo"]]]
                            p["fundamentals_source"] = alt[p["yahoo"]]
            except Exception as e:
                log(f"[fundamentals] cross-exchange fallback failed: {e}")
    except Exception as e:
        log(f"[fundamentals] attach failed: {e}")
        for p in picks:
            p.setdefault("fundamentals", None)
    return picks
