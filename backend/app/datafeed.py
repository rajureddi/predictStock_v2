"""Price data: official Bhavcopy history panels FIRST (NSE+BSE, includes BSE
scrips Yahoo doesn't carry), Yahoo Finance as fallback / history extender.

Panels (data/history/{nse,bse}_panel.csv.gz, built by app.bhavcopy) are loaded
once per process and sliced per ticker. When a local frame is too short we
merge in Yahoo rows (local wins on overlapping dates — it is exchange data).
"""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, yfinance as yf
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"; CACHE.mkdir(parents=True, exist_ok=True)
HIST = ROOT / "data" / "history"
OHLCV = ["Open", "High", "Low", "Close", "Volume"]

_PANEL_DICTS = {}  # exchange -> {yahoo_ticker: DataFrame}

def _clean(df):
    if df is None or len(df) == 0: return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy(); df.columns = [c[0] for c in df.columns]
    if "Close" not in df.columns: return None
    df = df.dropna(subset=["Close"])
    if len(df) == 0: return None
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("Open","High","Low","Close","Volume"):
        if col not in df.columns: return None
    return df

def _panel_dict(exchange):
    """{ticker: OHLCV(+Deliv) DataFrame} for one exchange, built once."""
    if exchange in _PANEL_DICTS: return _PANEL_DICTS[exchange]
    f = HIST / f"{exchange}_panel.csv.gz"
    out = {}
    if f.exists():
        try:
            panel = pd.read_csv(f, parse_dates=["Date"])
            panel = panel.set_index("Date").sort_index()
            for key, g in panel.groupby("Key"):
                g = g.drop(columns=["Key"])
                g.index.name = "Date"
                out[str(key)] = _clean(g)
            out = {k: v for k, v in out.items() if v is not None}
        except Exception:
            out = {}
    _PANEL_DICTS[exchange] = out
    return out

def local_history(ticker):
    """Bhavcopy-store frame for a .NS/.BO ticker, or None."""
    if ticker.endswith(".NS"): ex = "nse"
    elif ticker.endswith(".BO"): ex = "bse"
    else: return None
    df = _panel_dict(ex).get(ticker)
    return df.copy() if df is not None else None

def _merge(local, yahoo):
    """Union of both frames; on overlapping dates the local (exchange) row
    wins because it is concatenated last and duplicates keep the last."""
    if local is None: return yahoo
    if yahoo is None: return local
    cols = list(dict.fromkeys(list(yahoo.columns) + list(local.columns)))
    both = pd.concat([yahoo.reindex(columns=cols), local.reindex(columns=cols)], axis=0)
    both = both[~both.index.duplicated(keep="last")].sort_index()
    return _clean(both)

def _yahoo_batch(tickers, period):
    out = {}
    if not tickers: return out
    try:
        raw = yf.download(tickers, period=period, interval="1d", group_by="ticker",
                          auto_adjust=False, threads=True, progress=False, timeout=3)
    except Exception:
        return out
    if raw is None or len(raw) == 0: return out
    if len(tickers) == 1:
        d = _clean(raw)
        if d is not None: out[tickers[0]] = d
        return out
    for t in tickers:
        try:
            if t in raw.columns.get_level_values(0):
                d = _clean(raw[t])
                if d is not None: out[t] = d
        except Exception:
            continue
    return out

def download_batch(tickers, period="1y"):
    """Returns {ticker: DataFrame}. Local bhavcopy store first; Yahoo only
    for tickers whose local frame is missing or too short (merged)."""
    out, need = {}, []
    # 1y is fully covered by the ~13-month bhavcopy store; a 2y request
    # still merges Yahoo's longer history when it exists (local wins on
    # overlapping dates) so stage-2 backtests keep their depth.
    min_local = 480 if period == "2y" else 120
    for t in tickers:
        loc = local_history(t)
        if loc is not None and len(loc) >= min_local:
            out[t] = loc
        elif loc is not None and t.endswith(".BO") and len(loc) >= 60:
            # BSE numerical scrips have excellent local Bhavcopy coverage (~260 days);
            # Yahoo Finance almost never carries reliable history for 6-digit .BO codes.
            # Using local Bhavcopy directly avoids massive connection timeouts.
            out[t] = loc
        elif loc is not None and period != "2y" and len(loc) >= 30:
            # Thin local frame (mostly BSE scrips that trade sparsely):
            # Yahoo carries nothing better for these and bulk-fetching
            # thousands of dead .BO tickers stalls the run — accept the
            # local frame; the caller's min-rows rule decides inclusion.
            out[t] = loc
        else:
            need.append(t)
            if loc is not None: out[t] = loc  # keep as fallback if Yahoo fails
    if need:
        yh = _yahoo_batch(need, period=period)
        for t in need:
            if t in yh:
                merged = _merge(out.get(t), yh[t])
                if merged is not None: out[t] = merged
    return out

def download_one(ticker, period="2y", use_cache=True):
    f = CACHE / f"{ticker.replace('^','IDX_')}.csv"
    if use_cache and f.exists():
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            if len(df): return _clean(df)
        except Exception: pass
    res = download_batch([ticker], period=period)
    df = res.get(ticker)
    if df is not None:
        try: df.to_csv(f)
        except Exception: pass
    return df

def nifty_close(period="2y"):
    df = download_one("^NSEI", period=period)
    return df["Close"] if df is not None else None

def history_series(ticker, days=90):
    """Recent OHLC rows for charts: [{date, open, high, low, close, volume}]."""
    df = local_history(ticker)
    if df is None or len(df) < 5:
        df = download_one(ticker, period="1y")
    if df is None: return []
    df = df.tail(days)
    return [dict(date=str(idx.date()), open=round(float(r["Open"]), 2), high=round(float(r["High"]), 2),
                 low=round(float(r["Low"]), 2), close=round(float(r["Close"]), 2),
                 volume=int(r["Volume"]) if pd.notna(r["Volume"]) else 0)
            for idx, r in df.iterrows()]
