"""Price data: official Bhavcopy history panels FIRST (NSE+BSE, includes BSE
scrips Yahoo doesn't carry), Yahoo Finance as fallback / history extender.

Panels (data/history/{nse,bse}_panel.csv.gz, built by app.bhavcopy) are loaded
once per process and sliced per ticker. When a local frame is too short we
merge in Yahoo rows (local wins on overlapping dates — it is exchange data).
"""
import warnings; warnings.filterwarnings("ignore")
import pickle, threading
import numpy as np, pandas as pd, yfinance as yf
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"; CACHE.mkdir(parents=True, exist_ok=True)
HIST = ROOT / "data" / "history"
OHLCV = ["Open", "High", "Low", "Close", "Volume"]

_PANEL_DICTS = {}  # exchange -> {yahoo_ticker: DataFrame}
_PANEL_CACHE_VER = 2  # bumped for corporate-action (split/bonus) adjustment

# Canonical Indian corporate-action (split / bonus) adjustment factors:
# 1.5 (1:2 bonus), 2.0 (1:1 bonus / 1:2 split), 2.5 (3:2 bonus), 3.0 (2:1 bonus),
# 4.0 (3:1 bonus), 5.0 (1:5 split), 6.0 (5:1 bonus), 10.0 (1:10 split).
_CA_FACTORS = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 10.0)


def adjust_corporate_actions(df):
    """Detects unadjusted overnight stock splits & bonus issues in raw NSE/BSE
    Bhavcopy series (where nominal price drops by a canonical split/bonus factor
    >= 1.44x overnight) and backward-adjusts historical OHLC + Volume/DelivQty."""
    if df is None or len(df) < 3:
        return df
    c = df["Close"].to_numpy(dtype=float)
    o = df["Open"].to_numpy(dtype=float)
    prev_c = c[:-1]
    next_o = o[1:]
    next_c = c[1:]
    valid = (prev_c > 0) & (next_o > 0) & (next_c > 0)
    if not valid.any():
        return df

    r_open = np.where(valid, prev_c / np.maximum(next_o, 1e-9), 1.0)
    r_close = np.where(valid, prev_c / np.maximum(next_c, 1e-9), 1.0)
    # Candidate ex-dates: overnight drop >= 31% (factor >= 1.44, outside normal 20% circuit limits)
    cand_idx = np.where((r_open >= 1.44) & (r_close >= 1.40))[0]
    if len(cand_idx) == 0:
        return df

    out = None
    for idx in cand_idx:
        ro_val, rc_val = float(r_open[idx]), float(r_close[idx])
        best_f = min(_CA_FACTORS, key=lambda f: abs(ro_val - f) / f)
        if abs(ro_val - best_f) / best_f <= 0.065 and abs(rc_val - best_f) / best_f <= 0.095:
            if out is None:
                out = df.copy()
                for col in ("Open", "High", "Low", "Close", "Volume"):
                    if col in out.columns:
                        out[col] = out[col].astype(float)
            pos = idx + 1  # ex-date row position; adjust all rows strictly before pos
            for col in ("Open", "High", "Low", "Close"):
                out.iloc[:pos, out.columns.get_loc(col)] /= best_f
            if "Volume" in out.columns:
                out.iloc[:pos, out.columns.get_loc("Volume")] *= best_f
            if "DelivQty" in out.columns:
                out["DelivQty"] = pd.to_numeric(out["DelivQty"], errors="coerce")
                out.iloc[:pos, out.columns.get_loc("DelivQty")] *= best_f
    return out if out is not None else df


def _clean(df):
    if df is None or len(df) == 0: return None
    if isinstance(df.columns, pd.MultiIndex):
        # single-ticker group_by="ticker" frames put the ticker on level 0 and the
        # OHLCV field on level 1 — keep whichever level actually carries "Close"
        df = df.copy()
        lv = [i for i in range(df.columns.nlevels) if "Close" in df.columns.get_level_values(i)]
        df.columns = list(df.columns.get_level_values(lv[0])) if lv else [c[0] for c in df.columns]
    if "Close" not in df.columns: return None
    df = df.dropna(subset=["Close"])
    if len(df) == 0: return None
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("Open","High","Low","Close","Volume"):
        if col not in df.columns: return None
    return adjust_corporate_actions(df)

_PANEL_LOCK = threading.Lock()

def _panel_dict(exchange):
    """{ticker: OHLCV(+Deliv) DataFrame} for one exchange, built once.
    The parsed dict is pickled next to the CSV and reused while the CSV's
    mtime is unchanged; parsing the CSV from scratch takes ~20s."""
    if exchange in _PANEL_DICTS: return _PANEL_DICTS[exchange]
    with _PANEL_LOCK:
        if exchange in _PANEL_DICTS: return _PANEL_DICTS[exchange]
        f = HIST / f"{exchange}_panel.csv.gz"
        pk = HIST / f"{exchange}_panel.dict.pkl"
        out = {}
        if f.exists():
            mtime = f.stat().st_mtime
            try:
                if pk.exists():
                    with open(pk, "rb") as fh:
                        saved = pickle.load(fh)
                    if saved.get("mtime") == mtime and saved.get("ver") == _PANEL_CACHE_VER:
                        out = saved["data"]
            except Exception:
                out = {}
            if not out:
                try:
                    panel = pd.read_csv(f, parse_dates=["Date"])
                    panel = panel.set_index("Date").sort_index()
                    for key, g in panel.groupby("Key"):
                        g = g.drop(columns=["Key"])
                        g.index.name = "Date"
                        out[str(key)] = _clean(g)
                    out = {k: v for k, v in out.items() if v is not None}
                    try:
                        with open(pk, "wb") as fh:
                            pickle.dump({"mtime": mtime, "ver": _PANEL_CACHE_VER, "data": out}, fh, protocol=pickle.HIGHEST_PROTOCOL)
                    except Exception:
                        pass
                except Exception:
                    out = {}
        _PANEL_DICTS[exchange] = out
        return out

def warm_panels():
    for ex in ("nse", "bse"):
        _panel_dict(ex)

def local_history(ticker):
    """Bhavcopy-store frame for a .NS/.BO ticker, or None."""
    if ticker.endswith(".NS"): ex = "nse"
    elif ticker.endswith(".BO"): ex = "bse"
    else: return None
    df = _panel_dict(ex).get(ticker)
    return df.copy() if df is not None else None

def _merge(local, yahoo):
    """Union of both frames; on overlapping dates the local (exchange) row
    wins because it is concatenated last and duplicates keep the last.
    Aligns any corporate-action split factor across the Yahoo-to-Bhavcopy seam."""
    if local is None: return yahoo
    if yahoo is None: return local
    try:
        overlap = local.index.intersection(yahoo.index)
        if len(overlap) > 0:
            t0 = overlap[0]
            lc = float(local.loc[t0, "Close"])
            yc = float(yahoo.loc[t0, "Close"])
            if lc > 0 and yc > 0:
                seam_ratio = lc / yc
                if abs(seam_ratio - 1.0) > 0.08:
                    yahoo = yahoo.copy()
                    for col in ("Open", "High", "Low", "Close"):
                        if col in yahoo.columns:
                            yahoo[col] = yahoo[col].astype(float) * seam_ratio
                    if "Volume" in yahoo.columns:
                        yahoo["Volume"] = yahoo["Volume"].astype(float) / seam_ratio
    except Exception:
        pass
    cols = list(dict.fromkeys(list(yahoo.columns) + list(local.columns)))
    both = pd.concat([yahoo.reindex(columns=cols), local.reindex(columns=cols)], axis=0)
    both = both[~both.index.duplicated(keep="last")].sort_index()
    return _clean(both)

def _yahoo_batch(tickers, period):
    from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
    out = {}
    if not tickers: return out
    # Check local index cache first for ^NSEI / ^INDIAVIX / sector indices so index queries never stall on Yahoo
    rem = []
    for t in tickers:
        if str(t).startswith("^") or str(t) == "NIFTY_FIN_SERVICE.NS":
            f = CACHE / f"{str(t).replace('^','IDX_')}.csv"
            if f.exists():
                try:
                    df_c = pd.read_csv(f, index_col=0, parse_dates=True)
                    if len(df_c) >= 10:
                        out[t] = _clean(df_c)
                        continue
                except Exception:
                    pass
        rem.append(t)
    if not rem:
        return out

    # Guard against future-dated system clocks (e.g. late 2026) where short relative
    # periods ('5d', '1mo', '3mo', '6mo') compute a start date in the future on Yahoo.
    yf_period = "2y" if period in ("5d", "1mo", "3mo", "6mo", "1y") else period

    ex = ThreadPoolExecutor(max_workers=1)
    raw = None
    try:
        fut = ex.submit(
            yf.download,
            rem,
            period=yf_period,
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=False,
            progress=False,
            timeout=4,
        )
        done, _ = futures_wait([fut], timeout=5.5)
        if fut in done:
            raw = fut.result()
    except Exception:
        raw = None
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    if raw is None or len(raw) == 0:
        return out
    if len(rem) == 1:
        d = _clean(raw)
        if d is not None:
            out[rem[0]] = d
            if str(rem[0]).startswith("^") or str(rem[0]) == "NIFTY_FIN_SERVICE.NS":
                try:
                    d.to_csv(CACHE / f"{str(rem[0]).replace('^','IDX_')}.csv")
                except Exception:
                    pass
        return out
    for t in rem:
        try:
            if t in raw.columns.get_level_values(0):
                d = _clean(raw[t])
                if d is not None:
                    out[t] = d
                    if str(t).startswith("^") or str(t) == "NIFTY_FIN_SERVICE.NS":
                        try:
                            d.to_csv(CACHE / f"{str(t).replace('^','IDX_')}.csv")
                        except Exception:
                            pass
        except Exception:
            continue
    return out


def download_batch(tickers, period="1y"):
    """Returns {ticker: DataFrame}. Local official Bhavcopy store first (~290 trading
    days across 6,910 NSE+BSE equities); Yahoo only for indices or single-ticker
    queries missing from the local panel."""
    out, need = {}, []
    nse_loaded = bool(_panel_dict("nse"))
    bulk_mode = len(tickers) > 5
    for t in tickers:
        if str(t).startswith("^"):
            f = CACHE / f"{t.replace('^','IDX_')}.csv"
            if f.exists():
                try:
                    df_c = pd.read_csv(f, index_col=0, parse_dates=True)
                    if len(df_c) >= 10:
                        out[t] = _clean(df_c)
                        continue
                except Exception:
                    pass
        loc = local_history(t)
        if loc is not None and len(loc) >= 20:
            out[t] = loc
        elif bulk_mode and nse_loaded and (str(t).endswith(".NS") or str(t).endswith(".BO")):
            # Untraded / suspended scrip absent from official exchange Bhavcopy:
            # skip bulk Yahoo network calls so 8,000-stock scans never stall or deadlock.
            if loc is not None:
                out[t] = loc
        else:
            need.append(t)
            if loc is not None:
                out[t] = loc
    if need:
        yh = _yahoo_batch(need, period=period)
        for t in need:
            if t in yh:
                merged = _merge(out.get(t), yh[t])
                if merged is not None:
                    out[t] = merged
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

def expected_session_date():
    """Last NSE session whose official close should already be out. Weekends roll back to Friday.
    Before 16:00 IST the current day's close is not expected yet."""
    import datetime
    ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    d = ist.date()
    if ist.time() < datetime.time(16, 0):
        d -= datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d


def _last_session_date(df):
    if df is None or len(df) == 0:
        return None
    idx = df.index[-1]
    return idx.date() if hasattr(idx, "date") else None


def _yahoo_fill(tickers):
    """Newer daily bars for tickers whose local panel is behind the last session.
    Chunked so one slow download cannot drop the whole set."""
    out = {}
    for i in range(0, len(tickers), 8):
        try:
            out.update(_yahoo_batch(tickers[i:i + 8], period="1mo"))
        except Exception:
            pass
    return out


def with_latest_session(ticker, df=None):
    """One ticker's bars, with Yahoo appended when the bhavcopy panel is behind."""
    if df is None:
        df = local_history(ticker)
    if df is None or len(df) < 5:
        got = _yahoo_fill([ticker]).get(ticker)
        return got if got is not None else df
    last_d = _last_session_date(df)
    if last_d is not None and last_d < expected_session_date():
        extra = _yahoo_fill([ticker]).get(ticker)
        if extra is not None:
            df = _merge(df, extra)
    return df


def with_latest_sessions(tickers):
    """Same latest close the chart uses, for many tickers at once.
    A fresh local panel is returned as-is. A stale one is merged with newer Yahoo bars
    (local exchange rows win on dates both sources have)."""
    expected = expected_session_date()
    frames = {}
    need = []
    for t in tickers:
        df = local_history(t)
        frames[t] = df
        last_d = _last_session_date(df)
        if df is None or len(df) < 5 or last_d is None or last_d < expected:
            need.append(t)
    if need:
        for t, extra in _yahoo_fill(need).items():
            frames[t] = _merge(frames.get(t), extra)
    return frames


def history_series(ticker, days=90):
    """Recent OHLC rows for charts: [{date, open, high, low, close, volume}].
    The bhavcopy panel can lag the latest session; Yahoo fills only those newer bars.
    The last close here is the same number live quotes return."""
    df = local_history(ticker)
    if df is None or len(df) < 5:
        df = download_one(ticker, period="1y")
        if df is not None and _last_session_date(df) is not None and _last_session_date(df) < expected_session_date():
            df = with_latest_session(ticker, df)
    else:
        df = with_latest_session(ticker, df)
    if df is None: return []
    df = df.tail(days)
    return [dict(date=str(idx.date()), open=round(float(r["Open"]), 2), high=round(float(r["High"]), 2),
                 low=round(float(r["Low"]), 2), close=round(float(r["Close"]), 2),
                 volume=int(r["Volume"]) if pd.notna(r["Volume"]) else 0)
            for idx, r in df.iterrows()]
