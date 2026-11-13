"""Sector strength from official NSE sectoral indices (via Yahoo).

Each sector gets 1-week and 1-month returns, the same returns relative to
NIFTY, and whether the index is above its 50-DMA. Picks are mapped to a
sector index from their yfinance sector / industry label. Cached for 6 hours.
"""
import json, time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE_F = ROOT / "data" / "sector_strength_cache.json"
CACHE_SECS = 6 * 3600

SECTOR_INDICES = {
    "Bank": "^NSEBANK",
    "PSU Bank": "^CNXPSUBANK",
    "Financial Services": "NIFTY_FIN_SERVICE.NS",
    "IT": "^CNXIT",
    "Pharma": "^CNXPHARMA",
    "Auto": "^CNXAUTO",
    "FMCG": "^CNXFMCG",
    "Consumption": "^CNXCONSUM",
    "Metal": "^CNXMETAL",
    "Commodities": "^CNXCMDT",
    "Energy": "^CNXENERGY",
    "Realty": "^CNXREALTY",
    "Media": "^CNXMEDIA",
    "Infra": "^CNXINFRA",
    "PSE": "^CNXPSE",
}

_YF_SECTOR_MAP = {
    "Technology": "IT",
    "Healthcare": "Pharma",
    "Financial Services": "Financial Services",
    "Consumer Cyclical": "Consumption",
    "Consumer Defensive": "FMCG",
    "Basic Materials": "Commodities",
    "Energy": "Energy",
    "Utilities": "Energy",
    "Real Estate": "Realty",
    "Communication Services": "Media",
    "Industrials": "Infra",
}


def map_sector(sector: Optional[str], industry: Optional[str] = None) -> Optional[str]:
    ind = (industry or "").lower()
    if "bank" in ind:
        return "Bank"
    if any(k in ind for k in ("auto", "vehicle", "tire", "tyre", "two-wheeler", "tractor")):
        return "Auto"
    if any(k in ind for k in ("steel", "aluminum", "aluminium", "copper", "zinc", "metal", "mining", "iron")):
        return "Metal"
    if any(k in ind for k in ("chemical", "fertilizer", "agrochemical", "cement", "paper")):
        return "Commodities"
    if any(k in ind for k in ("retail", "apparel", "footwear", "hotel", "restaurant", "luxury", "jewel", "consumer")):
        return "Consumption"
    if any(k in ind for k in ("packaged food", "beverage", "household", "personal products", "tobacco")):
        return "FMCG"
    if any(k in ind for k in ("aerospace", "defense", "defence", "railway", "shipbuilding", "engineering", "construction", "infrastructure")):
        return "Infra"
    return _YF_SECTOR_MAP.get(sector or "")


def _ret(c: pd.Series, n: int) -> Optional[float]:
    c = c.dropna()
    return round((float(c.iloc[-1]) / float(c.iloc[-1 - n]) - 1) * 100, 2) if len(c) > n else None


def compute(nifty_close: Optional[pd.Series], index_closes: Dict[str, pd.Series]) -> Dict[str, Any]:
    n5 = _ret(nifty_close, 5) if nifty_close is not None else None
    n21 = _ret(nifty_close, 21) if nifty_close is not None else None
    rows: List[Dict[str, Any]] = []
    for name, c in index_closes.items():
        c = c.dropna()
        if len(c) < 55:
            continue
        r5, r21 = _ret(c, 5), _ret(c, 21)
        rs1w = round(r5 - n5, 2) if r5 is not None and n5 is not None else None
        rs1m = round(r21 - n21, 2) if r21 is not None and n21 is not None else None
        accel = round(rs1w - (rs1m / 4.0), 2) if rs1w is not None and rs1m is not None else 0.0
        rows.append(dict(
            sector=name,
            ret_1w_pct=r5,
            ret_1m_pct=r21,
            rs_1w_pct=rs1w,
            rs_1m_pct=rs1m,
            rotation_accel_pct=accel,
            above_50dma=bool(float(c.iloc[-1]) > float(c.tail(50).mean())),
        ))
    rows.sort(key=lambda r: -((r["rs_1m_pct"] if r["rs_1m_pct"] is not None else -999) + 0.35 * (r.get("rotation_accel_pct") or 0.0)))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
        rs = r["rs_1m_pct"] or 0
        acc = r.get("rotation_accel_pct") or 0
        r["trend"] = "Leading" if (rs >= 2 or (rs >= 0.5 and acc >= 1.2)) and r["above_50dma"] else "Lagging" if rs <= -2 or not r["above_50dma"] else "Neutral"
    return dict(nifty_ret_1w_pct=n5, nifty_ret_1m_pct=n21, sectors=rows)


def _download(tickers: List[str], attempts: int = 1) -> Dict[str, pd.DataFrame]:
    """Loads sectoral indices from local cache or clock-safe 2y Yahoo batch."""
    from app import datafeed
    return datafeed.download_batch(tickers, period="2y")


def get_sector_strength(force: bool = False) -> Dict[str, Any]:
    if not force and CACHE_F.exists():
        try:
            cached = json.loads(CACHE_F.read_text(encoding="utf-8"))
            if time.time() - cached.get("ts", 0) < CACHE_SECS and cached.get("sectors"):
                return cached
        except Exception:
            pass
    from app import datafeed
    tickers = ["^NSEI"] + list(SECTOR_INDICES.values())
    data = _download(tickers)
    nifty = data.get("^NSEI")
    if nifty is None:
        try:
            nifty = datafeed.download_one("^NSEI", period="2y")
        except Exception:
            nifty = None
    closes = {name: data[t]["Close"] for name, t in SECTOR_INDICES.items() if t in data}
    out = compute(nifty["Close"] if nifty is not None else None, closes)
    out["ts"] = time.time()
    out["as_of"] = str(nifty.index[-1].date()) if nifty is not None and len(nifty) else None
    if out["sectors"] and out["nifty_ret_1m_pct"] is not None:
        try:
            CACHE_F.write_text(json.dumps(out), encoding="utf-8")
        except Exception:
            pass
    return out


def apply_momentum_penalty(picks: List[Dict[str, Any]], strength: Dict[str, Any]) -> None:
    """Bottom 3 sectors versus NIFTY lose 15 points. Other lagging sectors lose 8.
    Applied once, after the stock's sector label is known."""
    attach_sector_strength(picks, strength)
    rows = strength.get("sectors") or []
    n = len(rows)
    bottom = {r.get("sector") for r in rows if n >= 4 and (r.get("rank") or 0) > n - 3}
    for p in picks:
        if p.get("_sector_penalized"):
            continue
        in_bottom = bool(p.get("sector_index") and p.get("sector_index") in bottom)
        p["sector_bottom"] = in_bottom
        reasons = p.get("reasons")
        if not isinstance(reasons, list):
            reasons = []
            p["reasons"] = reasons
        if in_bottom:
            p["trader_score"] = max(0.0, float(p.get("trader_score") or 0) - 15.0)
            reasons.append("Parent sector is one of the 3 weakest versus NIFTY — left out of new swings (−15)")
        elif p.get("sector_trend") == "Lagging":
            p["trader_score"] = max(0.0, float(p.get("trader_score") or 0) - 8.0)
            reasons.append("Lagging sector momentum — penalized (-8 pts)")
        p["_sector_penalized"] = True


def attach_sector_strength(picks: List[Dict[str, Any]], strength: Dict[str, Any]) -> None:
    by_name = {r["sector"]: r for r in strength.get("sectors", [])}
    for p in picks:
        idx = map_sector(p.get("sector"), p.get("industry"))
        row = by_name.get(idx) if idx else None
        p["sector_index"] = idx
        p["sector_rank"] = row["rank"] if row else None
        p["sector_rs_1m_pct"] = row["rs_1m_pct"] if row else None
        p["sector_rotation_accel_pct"] = row.get("rotation_accel_pct") if row else None
        p["sector_trend"] = row["trend"] if row else None


def attach_sector_strength_pit(
    picks: List[Dict[str, Any]],
    index_closes_full: Dict[str, pd.Series],
    nifty_close_full: Optional[pd.Series],
    as_of_ts: pd.Timestamp,
) -> None:
    """Point-in-time sectoral index relative strength & rotation acceleration as of `as_of_ts` (zero lookahead)."""
    if not index_closes_full or nifty_close_full is None:
        return
    nc = nifty_close_full[nifty_close_full.index <= as_of_ts]
    sliced = {
        name: s[s.index <= as_of_ts]
        for name, s in index_closes_full.items()
        if s is not None
    }
    strength = compute(nc, sliced)
    attach_sector_strength(picks, strength)
