import json, sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import pipeline as pl
from app import scan as scan_mod
from app.allocate import allocate
from app import backtest as backtest_mod

app = FastAPI(title="MarketMind Pro", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
REPORTS = ROOT / "data" / "reports"

def _latest():
    f = REPORTS / "latest.json"
    if not f.exists(): return None
    return json.loads(f.read_text(encoding="utf-8"))

def _with_allocation(report):
    if report is None: return None
    budget = pl.get_budget()
    picks = list(report.get("picks", []))
    regime = report.get("market_regime") or {}
    alloc = allocate(picks, budget, size_mult=regime.get("size_mult", 1.0) or 1.0,
                     cash_pct=regime.get("cash_pct", 0.0) or 0.0) if budget else None
    report = dict(report); report["allocation"] = alloc
    if alloc:
        for i, p in enumerate(picks):
            if i < len(alloc["allocations"]):
                a = alloc["allocations"][i]
                p = dict(p); p.update(shares=a["shares"], invested=a["invested"], expected_value=a["expected_value"],
                                      expected_profit=a["expected_profit"], risk_inr=a.get("risk_inr"))
                picks[i] = p
        report["picks"] = picks
    return report

@app.get("/api/health")
def health(): return {"ok": True, "product": "MarketMind Pro"}

@app.get("/api/universe")
def universe():
    from app import universe as u
    d = u.load_universe(); return {"counts": d["counts"], "source_nse": d["source_nse"], "source_bse": d["source_bse"]}

@app.post("/api/scan/start")
def scan_start(): return scan_mod.start_scan()

@app.get("/api/scan/status")
def scan_status(): return scan_mod.get_status()

@app.get("/api/simulation/{symbol}")
def get_simulation(symbol: str, exchange: str = "NSE", replays: int = 1000):
    from app import simulation
    r = _latest() or {}
    pick = None
    for p in r.get("picks", []):
        if p.get("symbol") == symbol:
            pick = p
            break
    if not pick:
        pick = {"symbol": symbol, "exchange": exchange}
    sim = simulation.simulate_pick(pick, replays=min(replays, 5000))
    orb = simulation.check_orb_status(pick)
    return {"symbol": symbol, "simulation": sim, "orb": orb}

@app.get("/api/picks/latest")
def latest(): return _with_allocation(_latest()) or {"picks": [], "note": "No run yet — run scripts/weekly_run.py"}

@app.get("/api/backtest")
def backtest_summary():
    """Latest offline portfolio backtest (scripts/backtest_portfolio.py) with
    transaction costs and the NIFTY 200-DMA regime split."""
    f = REPORTS / "backtest_summary.json"
    if not f.exists():
        return {"available": False, "note": "Run backend/scripts/backtest_portfolio.py to generate data/reports/backtest_summary.json"}
    try:
        d = json.loads(f.read_text(encoding="utf-8")); d["available"] = True; return d
    except Exception as e:
        return {"available": False, "error": str(e)}

@app.get("/api/scanned")
def scanned():
    r = _latest()
    if not r: return {"stage_counts": {}, "top50": []}
    return {"stage_counts": r.get("stage_counts"), "universe_counts": r.get("universe_counts"), "top50": r.get("stage1_top50", []), "run_date": r.get("run_date"), "target_date": r.get("target_date")}

@app.get("/api/prices/{symbol}")
def prices(symbol: str, days: int = 90, exchange: str | None = None):
    """Recent OHLC for charts. Accepts a Yahoo ticker (RELIANCE.NS,
    500002.BO) or a plain symbol resolved via the universe (+exchange)."""
    from app import datafeed, universe as u
    yahoo = symbol
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        try:
            for l in u.load_universe()["listings"]:
                if exchange and l["exchange"] != exchange: continue
                if l["symbol"] == symbol or l.get("scrip_code") == symbol:
                    yahoo = l["yahoo"]; break
        except Exception: pass
    return {"symbol": symbol, "yahoo": yahoo, "days": days,
            "series": datafeed.history_series(yahoo, days=max(5, min(days, 365)))}

@app.get("/api/search")
def search_stocks(q: str = ""):
    """Full-universe search across ~7,987 NSE & BSE listings by symbol or company name."""
    q_str = q.strip()
    if not q_str:
        return {"results": []}

    from app import universe as u
    try:
        listings = u.load_universe().get("listings", [])
    except Exception:
        listings = []

    q_lower = q_str.lower()
    q_upper = q_str.upper()

    r = _latest() or {}
    known = {}
    for p in r.get("picks", []) + r.get("stage1_top50", []):
        sym = p.get("symbol")
        if sym and sym not in known:
            known[sym] = p

    exact_sym = []
    prefix_sym = []
    prefix_name = []
    contains_name = []

    for l in listings:
        sym = l.get("symbol", "")
        name = l.get("name", "")
        ex = l.get("exchange", "NSE")

        entry = {
            "symbol": sym,
            "name": name,
            "exchange": ex,
            "yahoo": l.get("yahoo", f"{sym}.NS"),
            "current_price": None,
            "predicted_return_pct": None,
            "trader_score": None
        }
        if sym in known:
            kp = known[sym]
            entry["current_price"] = kp.get("current_price")
            entry["predicted_return_pct"] = kp.get("predicted_return_pct")
            entry["trader_score"] = kp.get("trader_score")

        if sym.upper() == q_upper:
            exact_sym.append(entry)
        elif sym.upper().startswith(q_upper):
            prefix_sym.append(entry)
        elif name.lower().startswith(q_lower):
            prefix_name.append(entry)
        elif q_lower in name.lower():
            contains_name.append(entry)

        if len(exact_sym) + len(prefix_sym) + len(prefix_name) + len(contains_name) >= 40:
            break

    merged = exact_sym + prefix_sym + prefix_name + contains_name
    seen = set()
    results = []
    for m in merged:
        key = (m["symbol"], m["exchange"])
        if key not in seen:
            seen.add(key)
            results.append(m)
        if len(results) >= 12:
            break

    return {"results": results}

_PREDICT_CACHE = {}

@app.get("/api/predict/{symbol}")
def predict_stock(symbol: str, exchange: str = "NSE"):
    """On-demand 5-day ML walk-forward forecast and simulation for ANY searched stock."""
    import time
    symbol = symbol.strip().upper()
    r = _latest() or {}

    # 1. If it's already one of this week's evaluated picks, return immediately
    for p in r.get("picks", []):
        if p.get("symbol") == symbol and (not exchange or p.get("exchange") == exchange):
            return {"pick": p, "cached": True}

    # 2. Check in-memory forecast cache (10 min TTL)
    cache_key = f"{symbol}:{exchange}"
    now = time.time()
    if cache_key in _PREDICT_CACHE and (now - _PREDICT_CACHE[cache_key]["ts"] < 600):
        return {"pick": _PREDICT_CACHE[cache_key]["data"], "cached": True}

    from app import universe as u, datafeed, engine, simulation
    listings = u.load_universe().get("listings", [])
    match = None
    for l in listings:
        if l.get("symbol") == symbol:
            if not exchange or l.get("exchange") == exchange:
                match = l
                break
    if not match:
        match = {"symbol": symbol, "name": symbol, "exchange": exchange, "yahoo": f"{symbol}.NS"}

    yahoo = match.get("yahoo") or (f"{symbol}.BO" if exchange == "BSE" else f"{symbol}.NS")
    data = datafeed.download_batch([yahoo, "^NSEI"], period="2y")
    df = data.get(yahoo)
    if df is None or len(df) < 60:
        return {"error": f"Insufficient price data available for {symbol}"}

    nifty = data.get("^NSEI")
    nc = nifty["Close"] if nifty is not None else None

    try:
        ts = engine.trader_score(df, nc)
        fc = engine.walk_forward_and_forecast(df, nc)
    except Exception as e:
        return {"error": f"Forecast calculation error for {symbol}: {e}"}

    if not ts or not fc:
        return {"error": f"Could not compute forecast model for {symbol}"}

    m = ts["metrics"]
    pick = dict(
        symbol=match["symbol"],
        name=match.get("name", symbol),
        exchange=match.get("exchange", exchange),
        yahoo=yahoo,
        isin=match.get("isin"),
        current_price=round(m["price"], 2),
        trader_score=ts["score"],
        reasons=ts["reasons"],
        patterns=m["patterns"],
        support=m["support"],
        resistance=m["resistance"],
        high52=m["high52"],
        stop_loss=m["stop_loss"],
        target=m["target1"],
        target2=m["target2"],
        risk_reward=m["risk_reward"],
        rsi=round(m["rsi"], 1),
        adx=round(m["adx"], 1),
        delivery_pct=m.get("delivery_pct"),
        volume_ratio=round(m["vol_ratio"], 2),
        **fc
    )
    try:
        pick["simulation"] = simulation.simulate_pick(pick, replays=1000)
        pick["orb"] = simulation.check_orb_status(pick)
    except Exception:
        pass

    _PREDICT_CACHE[cache_key] = {"ts": now, "data": pick}
    return {"pick": pick, "cached": False}

_LIVE_CACHE = {}

def _resolve_yahoo_map(symbols: list[str], exchange_hints: dict[str, str] | None = None) -> dict[str, str]:
    exchange_hints = exchange_hints or {}
    uni_by_pair = {}
    uni_by_sym = {}
    try:
        from app import universe as u
        for l in u.load_universe().get("listings", []):
            sym, ex, yh = l.get("symbol"), l.get("exchange"), l.get("yahoo")
            if sym and yh:
                uni_by_pair[(sym, ex)] = yh
                if sym not in uni_by_sym:
                    uni_by_sym[sym] = yh
    except Exception:
        pass
    out = {}
    for s in symbols:
        ex = exchange_hints.get(s)
        yh = (uni_by_pair.get((s, ex)) if ex else None) or uni_by_pair.get((s, "NSE")) or uni_by_pair.get((s, "BSE")) or uni_by_sym.get(s)
        if not yh:
            yh = f"{s}.BO" if ex == "BSE" else f"{s}.NS"
        out[s] = yh
    return out


def get_live_quotes(symbols: list[str], exchange_hints: dict[str, str] | None = None) -> dict[str, float]:
    import time
    from app import datafeed
    now = time.time()
    res = {}
    missing = []
    for s in symbols:
        if s in _LIVE_CACHE and (now - _LIVE_CACHE[s]["ts"] < 120):
            res[s] = _LIVE_CACHE[s]["price"]
        else:
            missing.append(s)

    if not missing:
        return res

    sym_to_yh = _resolve_yahoo_map(missing, exchange_hints)

    # 1. Official Bhavcopy local panel + local cache fallback (covers BSE & NSE reliably)
    local_latest = {}
    for s in missing:
        yh = sym_to_yh.get(s)
        if not yh:
            continue
        df = datafeed.local_history(yh)
        if df is None or len(df) == 0:
            f = datafeed.CACHE / f"{yh}.csv"
            if f.exists():
                try:
                    import pandas as pd
                    df = pd.read_csv(f, index_col=0, parse_dates=True)
                except Exception:
                    df = None
        if df is not None and len(df) and "Close" in df:
            c_ser = df["Close"].dropna()
            if len(c_ser):
                local_latest[s] = round(float(c_ser.iloc[-1]), 2)

    # 2. Also check latest report prices as secondary fallback
    r = _latest()
    if r:
        for p in r.get("picks", []) + r.get("stage1_top50", []):
            sym = p.get("symbol")
            cp = p.get("current_price")
            if sym and cp and sym not in local_latest:
                local_latest[sym] = round(float(cp), 2)

    # 3. Try live Yahoo Finance quotes for .NS tickers (or .BO not covered by Bhavcopy)
    yh_to_sym = {yh: s for s, yh in sym_to_yh.items() if yh and (not yh.endswith(".BO") or s not in local_latest)}
    tickers = list(yh_to_sym.keys())
    if tickers:
        try:
            import yfinance as yf
            import pandas as pd
            df = yf.download(tickers, period="5d", progress=False, timeout=10, threads=True)
            if df is not None and len(df) and "Close" in df:
                close_obj = df["Close"]
                if isinstance(close_obj, pd.Series):
                    s_clean = close_obj.dropna()
                    if len(s_clean) and float(s_clean.iloc[-1]) > 0:
                        sym = yh_to_sym.get(tickers[0])
                        if sym:
                            p = round(float(s_clean.iloc[-1]), 2)
                            _LIVE_CACHE[sym] = {"price": p, "ts": now}
                            res[sym] = p
                else:
                    closes = close_obj.tail(1).to_dict()
                    for yh, row in closes.items():
                        sym = yh_to_sym.get(yh)
                        if not sym:
                            continue
                        for _ts, v in row.items():
                            if v == v and v > 0:
                                p = round(float(v), 2)
                                _LIVE_CACHE[sym] = {"price": p, "ts": now}
                                res[sym] = p
        except Exception:
            pass

    # 4. Fill any symbol not returned by Yahoo from official local Bhavcopy / report fallback
    for s in missing:
        if s not in res or res[s] is None:
            fallback = local_latest.get(s)
            if fallback:
                _LIVE_CACHE[s] = {"price": fallback, "ts": now}
                res[s] = fallback
    return res

@app.get("/api/live-quotes")
def live_quotes(symbols: str = ""):
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return {"quotes": get_live_quotes(sym_list)}


_INDICES_CACHE = {"ts": 0, "data": None}

@app.get("/api/market-indices")
def market_indices():
    import datetime, time
    now = time.time()
    if _INDICES_CACHE["data"] and (now - _INDICES_CACHE["ts"] < 120):
        return _INDICES_CACHE["data"]

    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    is_weekday = ist_now.weekday() < 5
    now_time = ist_now.time()
    market_open = is_weekday and (datetime.time(9, 15) <= now_time <= datetime.time(15, 30))

    data = {
        "nifty": {"price": 24340.50, "change_pct": 0.42, "name": "NIFTY 50"},
        "vix": {"price": 14.85, "change_pct": -1.20, "name": "INDIA VIX"},
        "market_open": market_open,
        "cutoff": "15:30 IST",
        "ist_time": ist_now.strftime("%H:%M IST")
    }

    try:
        import yfinance as yf
        df = yf.download(["^NSEI", "^INDIAVIX"], period="5d", progress=False, timeout=4)
        if df is not None and "Close" in df and len(df) >= 2:
            closes = df["Close"]
            if "^NSEI" in closes:
                s = closes["^NSEI"].dropna()
                if len(s) >= 2:
                    p1, p0 = float(s.iloc[-1]), float(s.iloc[-2])
                    data["nifty"] = {"price": round(p1, 2), "change_pct": round(((p1 - p0) / p0) * 100, 2), "name": "NIFTY 50"}
            if "^INDIAVIX" in closes:
                s = closes["^INDIAVIX"].dropna()
                if len(s) >= 2:
                    p1, p0 = float(s.iloc[-1]), float(s.iloc[-2])
                    data["vix"] = {"price": round(p1, 2), "change_pct": round(((p1 - p0) / p0) * 100, 2), "name": "INDIA VIX"}
    except Exception:
        pass

    _INDICES_CACHE["ts"] = now
    _INDICES_CACHE["data"] = data
    return data

@app.get("/api/history")
def history():
    import pandas as pd
    from app import datafeed
    out = []
    reports_data = []
    all_symbols = set()
    ex_hints = {}
    for f in sorted(REPORTS.glob("report-*.json"), reverse=True):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
            reports_data.append(r)
            for p in r.get("picks", []):
                if p.get("symbol"):
                    all_symbols.add(p["symbol"])
                    if p.get("exchange") and p["symbol"] not in ex_hints:
                        ex_hints[p["symbol"]] = p["exchange"]
        except Exception:
            continue

    quotes = get_live_quotes(list(all_symbols), ex_hints) if all_symbols else {}
    sym_to_yh = _resolve_yahoo_map(list(all_symbols), ex_hints) if all_symbols else {}
    nifty_close = None
    if reports_data:
        try: nifty_close = datafeed.nifty_close(period="2y")
        except Exception: nifty_close = None
    settled_trades = []

    for r in reports_data:
        picks_out = []
        target_dt = r.get("target_date")
        for p in r.get("picks", []):
            sym = p.get("symbol")
            cp = p.get("current_price")
            live = quotes.get(sym) or cp
            live_ret = round(((live - cp) / cp) * 100, 2) if cp and live else None
            act_price = p.get("actual_price")
            act_ret = p.get("actual_return_pct")
            # Auto-resolve actual outcome if target_date has been reached in official history
            if act_price is None and target_dt and sym in sym_to_yh and cp:
                try:
                    df_h = datafeed.local_history(sym_to_yh[sym])
                    if df_h is not None and len(df_h):
                        after = df_h[df_h.index >= pd.Timestamp(target_dt)]
                        if len(after):
                            act_price = round(float(after["Close"].iloc[0]), 2)
                            act_ret = round(((act_price - cp) / cp) * 100, 2)
                except Exception:
                    pass
            if act_price is not None and cp:
                reg = backtest_mod.regime_on(nifty_close, r.get("run_date")) if nifty_close is not None and r.get("run_date") else None
                t = backtest_mod.trade_from_pick(p, act_price, regime=reg)
                if t: t["run_date"] = r.get("run_date"); settled_trades.append(t)
            pick_full = dict(p)
            pick_full.update({
                "symbol": sym,
                "name": p.get("name") or sym,
                "exchange": p.get("exchange") or "NSE",
                "current_price": cp,
                "predicted_price": p.get("predicted_price"),
                "predicted_return_pct": p.get("predicted_return_pct"),
                "live_price": live,
                "live_return_pct": live_ret,
                "actual_price": act_price,
                "actual_return_pct": act_ret,
                "run_date": r.get("run_date"),
                "target_date": target_dt
            })
            picks_out.append(pick_full)
        out.append({
            "run_date": r.get("run_date"),
            "target_date": target_dt,
            "picks": picks_out,
            "market_regime": r.get("market_regime")
        })
    track = backtest_mod.compute_trade_stats(settled_trades)
    track["weeks_settled"] = len({t["run_date"] for t in settled_trades})
    track["weeks_total"] = len(reports_data)
    return {"weeks": out, "track_record": track}

class BudgetIn(BaseModel):
    budget_inr: float | None = None

@app.get("/api/screen/budget")
def get_budget(): return {"budget_inr": pl.get_budget()}

@app.post("/api/screen/budget")
def post_budget(body: BudgetIn):
    v = body.budget_inr
    if v is not None and v < 0: v = None
    pl.set_budget(v); return {"budget_inr": pl.get_budget()}
