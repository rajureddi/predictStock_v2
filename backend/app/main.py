import json, sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import auth as auth_mod
from app import pipeline as pl
from app import scan as scan_mod
from app.allocate import allocate
from app import backtest as backtest_mod

class SessionGate(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not auth_mod.auth_enabled() or not path.startswith("/api/"):
            return await call_next(request)
        if path in ("/api/auth/login", "/api/auth/logout", "/api/auth/me", "/api/health"):
            return await call_next(request)
        if auth_mod.read_token(request.cookies.get(auth_mod.COOKIE, "")):
            return await call_next(request)
        return JSONResponse({"detail": "Sign in required"}, status_code=401)

app = FastAPI(title="MarketMind Pro", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionGate)

class LoginIn(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def auth_login(body: LoginIn):
    if auth_mod.too_many_attempts():
        return JSONResponse({"ok": False, "error": "Too many attempts. Wait a few minutes."}, status_code=429)
    if not auth_mod.verify(body.username, body.password):
        auth_mod.note_failure()
        return JSONResponse({"ok": False, "error": "Those details do not match."}, status_code=401)
    response = JSONResponse({"ok": True, "username": auth_mod.load_account()["username"]})
    response.set_cookie(
        auth_mod.COOKIE, auth_mod.make_token(),
        max_age=auth_mod.MAX_AGE, httponly=True, samesite="lax", path="/",
    )
    return response

@app.post("/api/auth/logout")
def auth_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(auth_mod.COOKIE, path="/")
    return response

@app.get("/api/auth/me")
def auth_me(request: Request):
    if auth_mod.read_token(request.cookies.get(auth_mod.COOKIE, "")):
        return {"ok": True, "username": auth_mod.load_account()["username"]}
    return JSONResponse({"ok": False}, status_code=401)
REPORTS = ROOT / "data" / "reports"

@app.on_event("startup")
def _warm_price_panels():
    import threading
    from app import datafeed
    threading.Thread(target=datafeed.warm_panels, daemon=True).start()
    from app import morning
    threading.Thread(target=morning.loop, daemon=True).start()

def _latest():
    from app import report_store
    report = report_store.latest_report()
    if report:
        return report
    f = REPORTS / "latest.json"
    if not f.exists(): return None
    return json.loads(f.read_text(encoding="utf-8"))

def _with_allocation(report):
    if report is None: return None
    rules = pl.get_screen_rules()
    budget = rules.get("budget_inr")
    regime = report.get("market_regime") or {}
    want = int(regime.get("max_picks") or 5)
    pool = report.get("candidate_pool")
    if pool:
        picks = pl.select_picks_for_budget(pool, budget_inr=budget, want=max(want, 5), rules=rules)
    else:
        picks = [dict(p) for p in report.get("picks", [])]
    alloc = allocate(picks, budget, size_mult=regime.get("size_mult", 1.0) or 1.0,
                     cash_pct=regime.get("cash_pct", 0.0) or 0.0, budget_mode=True) if budget else None
    if alloc and budget:
        s_min, s_max = pl.budget_price_band(budget, want=max(want, 5))
        alloc["price_band_min"] = s_min
        alloc["price_band_max"] = s_max
    report = dict(report)
    report["allocation"] = alloc
    report["screen_rules"] = rules
    if alloc:
        for i, p in enumerate(picks):
            if i < len(alloc["allocations"]):
                a = alloc["allocations"][i]
                p = dict(p); p.update(shares=a["shares"], invested=a["invested"], expected_value=a["expected_value"],
                                      expected_profit=a["expected_profit"], risk_inr=a.get("risk_inr"))
                picks[i] = p
    else:
        for i, p in enumerate(picks):
            p = dict(p)
            for k in ("shares", "invested", "expected_value", "expected_profit", "risk_inr"):
                p.pop(k, None)
            picks[i] = p

    # Attach live market quotes to every pick
    symbols = [p["symbol"] for p in picks if p.get("symbol")]
    ex_hints = {p["symbol"]: p.get("exchange", "NSE") for p in picks if p.get("symbol")}
    try:
        quotes = get_live_quotes(symbols, ex_hints)
    except Exception:
        quotes = {}

    updated_picks = []
    for p in picks:
        p = dict(p)
        sym = p.get("symbol")
        cp = p.get("current_price")
        live = quotes.get(sym) or cp
        if live:
            p["live_price"] = live
            p["live_return_pct"] = round(((live - cp) / cp) * 100, 2) if cp else 0.0
        updated_picks.append(p)

    report["picks"] = updated_picks
    return report

@app.get("/api/health")
def health(): return {"ok": True, "product": "MarketMind Pro"}

@app.get("/api/universe")
def universe():
    from app import universe as u
    d = u.load_universe(); return {"counts": d["counts"], "source_nse": d["source_nse"], "source_bse": d["source_bse"]}

@app.post("/api/scan/start")
def scan_start(fresh: bool = False):
    if fresh:
        _PREDICT_CACHE.clear()
    return scan_mod.start_scan(fresh=fresh)

@app.post("/api/scan/reset-today")
def scan_reset_today():
    _PREDICT_CACHE.clear()
    return scan_mod.reset_today_predictions()

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

@app.get("/api/sectors/heatmap")
def sectors_heatmap(refresh: bool = False):
    from app import sector_strength, sectors as sectors_mod
    data = dict(sector_strength.get_sector_strength(force=refresh))
    rep = _latest() or {}
    picks = rep.get("picks", [])
    cache = sectors_mod._load()
    out = []
    for p in picks:
        idx = p.get("sector_index")
        if not idx:
            from app.simulation import resolve_yahoo_ticker
            info = (cache.get(resolve_yahoo_ticker(p)) or {}).get("data") or {}
            idx = sector_strength.map_sector(p.get("sector") or info.get("sector"), p.get("industry") or info.get("industry"))
        out.append(dict(symbol=p.get("symbol"), name=p.get("name"), sector=p.get("sector"), sector_index=idx))
    data["picks"] = out
    return data

class BacktestRunIn(BaseModel):
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    weeks: Optional[int] = 52
    top_picks: Optional[int] = 5

@app.get("/api/backtest")
def backtest_summary():
    from app import backtest_engine
    return backtest_engine.get_backtest_results()

@app.post("/api/backtest/start")
def backtest_start(body: BacktestRunIn):
    from app import backtest_engine
    started = backtest_engine.start_background_backtest(
        from_date=body.from_date,
        to_date=body.to_date,
        weeks=body.weeks or 52,
        top_picks=body.top_picks or 5
    )
    return {"started": started, "message": "Backtest started" if started else "Already running"}

@app.get("/api/backtest/status")
def backtest_status():
    from app import backtest_engine
    return backtest_engine.get_backtest_status()

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

    from app import trade_rules
    m = ts["metrics"]
    pick = dict(
        symbol=match["symbol"],
        name=match.get("name", symbol),
        exchange=match.get("exchange", exchange),
        yahoo=yahoo,
        isin=match.get("isin"),
        current_price=round(m["price"], 2),
        trader_score=ts["score"],
        setup_type=m.get("setup_type"),
        reasons=ts["reasons"],
        patterns=m["patterns"],
        support=m["support"],
        resistance=m["resistance"],
        high52=m["high52"],
        atr=round(m["atr"], 2),
        stop_loss=m["stop_loss"],
        breakeven_at=m.get("breakeven_at"),
        breakeven_stop=m.get("breakeven_stop"),
        target=m["target1"],
        target2=m["target2"],
        risk_reward=m["risk_reward"],
        rsi=round(m["rsi"], 1),
        adx=round(m["adx"], 1),
        vcp_ratio=m.get("vcp_ratio"),
        clv=m.get("clv"),
        delivery_pct=m.get("delivery_pct"),
        dvr=m.get("dvr"),
        volume_ratio=round(m["vol_ratio"], 2),
        **trade_rules.relative_strength(df["Close"], nc),
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
    out = {}
    uni_by_sym = {}
    yahoo_by_sym_ex = {}
    try:
        from app import universe as u
        for l in u.load_universe().get("listings", []):
            sym, ex = l.get("symbol"), l.get("exchange")
            if sym and sym not in uni_by_sym:
                uni_by_sym[sym] = "BSE" if ex == "BSE" else "NSE"
            if sym and l.get("yahoo"):
                yahoo_by_sym_ex.setdefault((sym, "BSE" if ex == "BSE" else "NSE"), l["yahoo"])
    except Exception:
        pass

    for s in symbols:
        ex = exchange_hints.get(s) or uni_by_sym.get(s) or "NSE"
        # BSE listings are stored under their numeric scrip code (e.g. 513262.BO), not the symbol
        out[s] = (yahoo_by_sym_ex.get((s, ex))
                  or yahoo_by_sym_ex.get((s, "NSE" if ex == "BSE" else "BSE"))
                  or (f"{s}.BO" if ex == "BSE" else f"{s}.NS"))
    return out


def _frame_last_close(df):
    if df is None or len(df) == 0 or "Close" not in getattr(df, "columns", []):
        return None, None
    c = df["Close"].dropna()
    if not len(c):
        return None, None
    idx = c.index[-1]
    d = idx.date() if hasattr(idx, "date") else None
    return round(float(c.iloc[-1]), 2), d


def get_live_quotes(symbols: list[str], exchange_hints: dict[str, str] | None = None) -> dict[str, float]:
    import time
    from app import datafeed
    now = time.time()
    res = {}
    missing = []
    for s in symbols:
        if s in _LIVE_CACHE and (now - _LIVE_CACHE[s]["ts"] < 20):
            res[s] = _LIVE_CACHE[s]["price"]
        else:
            missing.append(s)

    if not missing:
        return res

    sym_to_yh = _resolve_yahoo_map(missing, exchange_hints)
    # Yahoo's last traded price. The daily bar is still yesterday's close until
    # the exchange file lands, which is why the desk was showing a stale "LIVE".
    tickers = list(dict.fromkeys(yh for yh in (sym_to_yh.get(s) for s in missing) if yh))
    try:
        live_px = datafeed.yahoo_last_prices(tickers)
    except Exception:
        live_px = {}
    missed = [sym_to_yh[s] for s in missing if sym_to_yh.get(s) and sym_to_yh[s] not in live_px]
    try:
        frames = datafeed.with_latest_sessions(missed) if missed else {}
    except Exception:
        frames = {}

    report_px = {}
    r = _latest()
    if r:
        for p in r.get("picks", []) + r.get("stage1_top50", []):
            sym, cp = p.get("symbol"), p.get("current_price")
            if sym and cp and sym not in report_px:
                report_px[sym] = round(float(cp), 2)

    for s in missing:
        yh = sym_to_yh.get(s)
        chosen = live_px.get(yh) if yh else None
        if not chosen:
            chosen, _asof = _frame_last_close(frames.get(yh) if yh else None)
        if not chosen:
            chosen = report_px.get(s)
        if chosen:
            _LIVE_CACHE[s] = {"price": chosen, "ts": now}
            res[s] = chosen
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
        "nifty": {"price": None, "change_pct": None, "name": "NIFTY 50"},
        "vix": {"price": None, "change_pct": None, "name": "INDIA VIX"},
        "market_open": market_open,
        "cutoff": "15:30 IST",
        "ist_time": ist_now.strftime("%H:%M IST")
    }

    try:
        from app import datafeed
        idx_frames = datafeed.download_batch(["^NSEI", "^INDIAVIX"], period="1y")
        nf_df = idx_frames.get("^NSEI")
        if nf_df is not None and "Close" in nf_df:
            s = nf_df["Close"].dropna()
            if len(s) >= 2:
                p1, p0 = float(s.iloc[-1]), float(s.iloc[-2])
                data["nifty"] = {"price": round(p1, 2), "change_pct": round(((p1 - p0) / p0) * 100, 2), "name": "NIFTY 50"}
        vx_df = idx_frames.get("^INDIAVIX")
        if vx_df is not None and "Close" in vx_df:
            s = vx_df["Close"].dropna()
            if len(s) >= 2:
                p1, p0 = float(s.iloc[-1]), float(s.iloc[-2])
                data["vix"] = {"price": round(p1, 2), "change_pct": round(((p1 - p0) / p0) * 100, 2), "name": "INDIA VIX"}
    except Exception:
        pass

    if data["nifty"]["price"] is None and _INDICES_CACHE["data"] and _INDICES_CACHE["data"]["nifty"]["price"]:
        return _INDICES_CACHE["data"]
    if data["nifty"]["price"] is not None:
        _INDICES_CACHE["ts"] = now
        _INDICES_CACHE["data"] = data
    return data

@app.get("/api/history")
def history():
    import pandas as pd
    from app import datafeed, report_store
    out = []
    all_symbols = set()
    ex_hints = {}
    # Every scan date is its own row. Collapsing to one ISO week hid later
    # scans in the same week (2 Nov was dropped once 3 Nov existed).
    reports_data = report_store.list_reports()
    for r in reports_data:
        for p in r.get("picks", []):
            if p.get("symbol"):
                all_symbols.add(p["symbol"])
                if p.get("exchange") and p["symbol"] not in ex_hints:
                    ex_hints[p["symbol"]] = p["exchange"]

    sym_to_yh = _resolve_yahoo_map(list(all_symbols), ex_hints) if all_symbols else {}
    # Official local closes, not a live download. Yahoo can stall this route
    # long enough that the scanned-date list never renders.
    quotes = {}
    for sym, yh in sym_to_yh.items():
        try:
            df_h = datafeed.local_history(yh)
            if df_h is not None and len(df_h):
                closes = df_h["Close"].dropna()
                if len(closes):
                    quotes[sym] = round(float(closes.iloc[-1]), 2)
        except Exception:
            pass
    nifty_close = None
    if reports_data:
        try:
            if (datafeed.CACHE / "IDX_NSEI.csv").exists():
                nifty_close = datafeed.nifty_close(period="2y")
        except Exception:
            nifty_close = None
    settled_by_key = {}

    for r in reports_data:
        picks_out = []
        target_dt = r.get("target_date")
        run_dt_str = r.get("run_date")
        for p in r.get("picks", []):
            sym = p.get("symbol")
            cp = p.get("current_price")
            live = quotes.get(sym) or cp
            live_ret = round(((live - cp) / cp) * 100, 2) if cp and live else None
            act_price = p.get("actual_price")
            act_ret = p.get("actual_return_pct")
            exit_reason = p.get("exit_reason")
            nifty_ret = None
            end_close = end_close_date = end_close_ret = None
            if target_dt and sym in sym_to_yh and cp:
                try:
                    df_e = datafeed.local_history(sym_to_yh[sym])
                    if df_e is not None and len(df_e) and df_e.index[-1] >= pd.Timestamp(target_dt):
                        upto = df_e[df_e.index <= pd.Timestamp(target_dt)]
                        if len(upto):
                            end_close = round(float(upto["Close"].iloc[-1]), 2)
                            end_close_date = str(upto.index[-1].date())
                            end_close_ret = round((end_close - cp) / cp * 100, 2)
                        # Always settle by the full trade plan (stop / target / Mooli Salamat breakeven / time exit)
                        # whenever official OHLC bars cover the holding window, overriding legacy raw-close snapshots.
                        window = df_e[(df_e.index > pd.Timestamp(run_dt_str)) & (df_e.index <= pd.Timestamp(target_dt))]
                        if len(window):
                            atr_est = float(p.get("atr") or (cp * 0.02))
                            be_at = p.get("breakeven_at") or round(cp + 0.75 * atr_est, 2)
                            be_stop = p.get("breakeven_stop") or round(cp * 1.0042, 2)
                            ex = backtest_mod.simulate_exit(
                                window, cp, p.get("stop_loss"), p.get("target"), len(window),
                                breakeven_at=be_at, breakeven_stop=be_stop
                            )
                            if ex:
                                act_price = round(float(ex["exit"]), 2)
                                act_ret = round(((act_price - cp) / cp) * 100, 2)
                                exit_reason = ex["reason"]
                except Exception:
                    pass
            if act_price is not None and nifty_close is not None and run_dt_str and target_dt:
                try:
                    n0 = nifty_close[nifty_close.index <= pd.Timestamp(run_dt_str)]
                    n1 = nifty_close[nifty_close.index <= pd.Timestamp(target_dt)]
                    if len(n0) and len(n1):
                        nifty_ret = round((float(n1.iloc[-1]) / float(n0.iloc[-1]) - 1) * 100, 2)
                except Exception:
                    pass
            if act_price is not None and cp:
                reg = backtest_mod.regime_on(nifty_close, run_dt_str) if nifty_close is not None and run_dt_str else None
                t = backtest_mod.trade_from_pick(p, act_price, regime=reg)
                if t:
                    t["run_date"] = run_dt_str
                    # Deduplicate identical symbol within the same ISO week for aggregate track_record
                    # (keeps the earliest scan of that week while preserving every scan row in `weeks`)
                    try:
                        iso = pd.Timestamp(run_dt_str).isocalendar()
                        dedup_key = (sym, int(iso.year), int(iso.week))
                    except Exception:
                        dedup_key = (sym, run_dt_str)
                    if dedup_key not in settled_by_key or str(run_dt_str) < str(settled_by_key[dedup_key].get("run_date", "")):
                        settled_by_key[dedup_key] = t
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
                "exit_reason": exit_reason,
                "end_close_price": end_close,
                "end_close_date": end_close_date,
                "end_close_return_pct": end_close_ret,
                "nifty_return_pct": nifty_ret,
                "alpha_pct": round(act_ret - nifty_ret, 2) if act_ret is not None and nifty_ret is not None else None,
                "run_date": r.get("run_date"),
                "target_date": target_dt
            })
            picks_out.append(pick_full)
        out.append({
            "run_date": r.get("run_date"),
            "target_date": target_dt,
            "picks": picks_out,
            "market_regime": r.get("market_regime"),
            "no_trade": r.get("no_trade", False),
            "no_trade_reason": r.get("no_trade_reason"),
        })
    settled_trades = list(settled_by_key.values())
    track = backtest_mod.compute_trade_stats(settled_trades)
    alphas = [p["alpha_pct"] for w in out for p in w["picks"] if p.get("alpha_pct") is not None]
    track["avg_alpha_vs_nifty_pct"] = round(sum(alphas) / len(alphas), 2) if alphas else None
    track["no_trade_weeks"] = sum(1 for w in out if w.get("no_trade"))
    track["weeks_settled"] = len({t["run_date"] for t in settled_trades})
    track["weeks_total"] = len(reports_data)
    track["scans_settled"] = track["weeks_settled"]
    track["scans_total"] = track["weeks_total"]
    return {
        "weeks": out,
        "scanned_dates": [r.get("run_date") for r in reports_data if r.get("run_date")],
        "track_record": track,
    }

class BudgetIn(BaseModel):
    budget_inr: float | None = None

class ScreenRulesIn(BaseModel):
    budget_inr: Optional[float] = None
    price_cap_mode: Optional[str] = "moderate"
    min_stock_price: Optional[float] = None
    max_stock_price: Optional[float] = None
    min_profit_inr: Optional[float] = 100.0
    profit_basis: Optional[str] = "auto"

@app.get("/api/screen/rules")
def get_screen_rules_endpoint():
    return pl.get_screen_rules()

@app.post("/api/screen/rules")
def post_screen_rules_endpoint(body: ScreenRulesIn):
    updates = body.dict(exclude_unset=True)
    if "budget_inr" in updates and updates["budget_inr"] is not None and updates["budget_inr"] <= 0:
        updates["budget_inr"] = None
    cfg = pl.set_screen_rules(updates)
    try:
        from app import report_store
        rep = _latest()
        if rep and rep.get("candidate_pool"):
            updated = _with_allocation(rep)
            if updated:
                report_store.save_report(updated)
                (REPORTS / "latest.json").write_text(json.dumps(updated, indent=1, default=str), encoding="utf-8")
    except Exception:
        pass
    return cfg

@app.get("/api/screen/budget")
def get_budget(): return {"budget_inr": pl.get_budget()}

@app.post("/api/screen/budget")
def post_budget(body: BudgetIn):
    v = body.budget_inr
    if v is not None and v <= 0: v = None
    pl.set_budget(v)
    try:
        from app import report_store
        rep = _latest()
        if rep and rep.get("candidate_pool"):
            updated = _with_allocation(rep)
            if updated:
                report_store.save_report(updated)
                (REPORTS / "latest.json").write_text(json.dumps(updated, indent=1, default=str), encoding="utf-8")
    except Exception:
        pass
    return {"budget_inr": pl.get_budget()}

# ---------- Alerts (NSE/BSE stops, targets, 15:20 IST review) ----------
class AlertAddIn(BaseModel):
    symbol: str
    exchange: Optional[str] = "NSE"
    type: str
    price: Optional[float] = None
    pct: Optional[float] = None
    at: Optional[str] = None
    note: Optional[str] = ""
    entry_price: Optional[float] = None
    direction: Optional[str] = None

class AlertToggleIn(BaseModel):
    id: str
    enabled: bool = True

class AlertResetIn(BaseModel):
    id: Optional[str] = None

def _alert_quotes(rules):
    from app import alerts as alerts_mod
    syms, hints = [], {}
    for rule in rules:
        if rule.get("type") in alerts_mod.NO_QUOTE:
            continue
        sym = (rule.get("symbol") or "").upper()
        if sym and sym not in hints:
            syms.append(sym)
            hints[sym] = rule.get("exchange") or "NSE"
    if not syms:
        return {}
    try:
        return get_live_quotes(syms, hints)
    except Exception:
        return {}

@app.get("/api/alerts")
def alerts_get():
    from app import alerts as alerts_mod
    doc = alerts_mod.load_rules()
    return alerts_mod.snapshot(_alert_quotes(doc["rules"]))

@app.post("/api/alerts/sync")
def alerts_sync():
    from app import alerts as alerts_mod
    report = _latest() or {}
    alerts_mod.sync_from_picks(report.get("picks") or [])
    doc = alerts_mod.load_rules()
    return alerts_mod.snapshot(_alert_quotes(doc["rules"]))

@app.post("/api/alerts/check")
def alerts_check():
    from app import alerts as alerts_mod
    doc = alerts_mod.load_rules()
    return alerts_mod.check(_alert_quotes(doc["rules"]))

@app.post("/api/alerts/reset")
def alerts_reset(body: AlertResetIn):
    from app import alerts as alerts_mod
    return alerts_mod.reset(body.id)

@app.post("/api/alerts/add")
def alerts_add(body: AlertAddIn):
    from app import alerts as alerts_mod
    return alerts_mod.add_rule(body.dict())

@app.post("/api/alerts/toggle")
def alerts_toggle(body: AlertToggleIn):
    from app import alerts as alerts_mod
    return alerts_mod.set_enabled(body.id, body.enabled)

# ---------- Portfolio (saved for the morning email) ----------
class HoldingIn(BaseModel):
    symbol: str
    exchange: Optional[str] = "NSE"
    name: Optional[str] = ""
    shares: Optional[float] = 0
    buy: Optional[float] = 0
    added: Optional[str] = ""
    predicted: Optional[float] = None
    target: Optional[float] = None
    stop: Optional[float] = None

class PortfolioIn(BaseModel):
    holdings: List[HoldingIn] = []

@app.get("/api/portfolio")
def portfolio_get():
    from app import mailer
    return {"holdings": mailer.load_portfolio()}

@app.post("/api/portfolio")
def portfolio_save(body: PortfolioIn):
    from app import mailer
    return mailer.save_portfolio([h.dict() for h in body.holdings])

# ---------- Mail (weekly picks report) ----------
class MailIn(BaseModel):
    to: Optional[str] = None
    from_addr: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    scan_start: Optional[str] = None
    email_by: Optional[str] = None

@app.get("/api/morning")
def morning_status():
    from app import morning
    return morning.status()

@app.get("/api/mail")
def mail_get():
    from app import mailer
    return mailer.public_config()

@app.post("/api/mail")
def mail_save(body: MailIn):
    from app import mailer
    return mailer.save_config(body.dict(exclude_unset=True))

@app.post("/api/mail/send")
def mail_send(test: bool = False):
    from app import mailer
    return mailer.send_report(_latest() or {}, test=test)

# ---------- Short-Term Quality Compounders Screener (On-Demand) ----------
@app.get("/api/short-term/picks")
def short_term_picks():
    from app import short_term_screener as sts
    return sts.get_latest_picks()

@app.post("/api/short-term/start")
def short_term_start():
    from app import short_term_screener as sts
    return sts.trigger_scan()

@app.get("/api/short-term/status")
def short_term_status():
    from app import short_term_screener as sts
    return sts.get_status()

# ---------- TradeAnalyser (TauricResearch/TradingAgents Multi-Agent Committee) ----------
class TradeAnalyserRunIn(BaseModel):
    symbol: str
    exchange: Optional[str] = "NSE"
    name: Optional[str] = None

@app.get("/api/trade-analyser/candidates")
def trade_analyser_candidates():
    from app import trade_analyser as ta
    candidates = ta.get_top10_candidates()
    cached = ta.load_cached_reports()
    for c in candidates:
        sym = c["symbol"]
        if sym in cached:
            c["has_report"] = True
            c["final_decision"] = cached[sym].get("final_decision")
            c["conviction_score"] = cached[sym].get("conviction_score")
            c["target1"] = cached[sym].get("target1")
            c["stop_loss"] = cached[sym].get("stop_loss")
        else:
            c["has_report"] = False
    return {"candidates": candidates}

@app.post("/api/trade-analyser/analyze")
def trade_analyser_analyze(body: TradeAnalyserRunIn):
    from app import trade_analyser as ta
    try:
        rep = ta.run_trading_agents_analysis(body.symbol, body.exchange or "NSE", body.name)
        return ta.sanitize_for_json(rep)
    except Exception as e:
        from fastapi.responses import JSONResponse
        status_code = 400 if "AI Engine Required" in str(e) else 500
        return JSONResponse(status_code=status_code, content={"error": str(e), "needs_ai": "AI Engine Required" in str(e), "symbol": body.symbol})

@app.get("/api/trade-analyser/report")
def trade_analyser_report(symbol: str):
    from app import trade_analyser as ta
    try:
        cached = ta.load_cached_reports()
        sym = symbol.strip().upper()
        if sym in cached:
            return ta.sanitize_for_json(cached[sym])
        candidates = ta.get_top10_candidates()
        cand = next((c for c in candidates if c["symbol"] == sym), None)
        ex = cand.get("exchange", "NSE") if cand else "NSE"
        nm = cand.get("name") if cand else sym
        rep = ta.run_trading_agents_analysis(sym, ex, nm)
        return ta.sanitize_for_json(rep)
    except Exception as e:
        from fastapi.responses import JSONResponse
        status_code = 400 if "AI Engine Required" in str(e) else 500
        return JSONResponse(status_code=status_code, content={"error": str(e), "needs_ai": "AI Engine Required" in str(e), "symbol": symbol})

@app.post("/api/trade-analyser/batch")
def trade_analyser_batch():
    from app import trade_analyser as ta
    started = ta.batch_analyze_top10()
    return {"status": "started" if started else "already_running"}

@app.get("/api/trade-analyser/status")
def trade_analyser_status():
    from app import trade_analyser as ta
    return ta.get_analysis_status()

@app.get("/api/trade-analyser/offline")
def trade_analyser_offline():
    from app import trade_analyser as ta
    return ta.load_offline_screen()

@app.post("/api/trade-analyser/offline")
def trade_analyser_offline_start():
    from app import trade_analyser as ta
    started = ta.start_offline_screen()
    return {"status": "started" if started else "already_running"}

@app.get("/api/trade-analyser/offline/status")
def trade_analyser_offline_status():
    from app import trade_analyser as ta
    return ta.get_offline_status()

# ---------- AI Provider & LLM Engine Settings ----------
class AIConfigIn(BaseModel):
    enabled: bool
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

class AITestIn(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None

@app.get("/api/trade-analyser/ai-config")
def get_ai_config():
    from app import llm_client
    return llm_client.get_sanitized_config()

@app.post("/api/trade-analyser/ai-config")
def update_ai_config(body: AIConfigIn):
    from app import llm_client
    try:
        curr = llm_client.load_ai_config()
        raw_key = body.api_key.strip() if body.api_key else ""
        if "••••" in raw_key:
            raw_key = curr.get("api_key", "")
        new_cfg = {
            "enabled": body.enabled,
            "provider": body.provider,
            "api_key": raw_key,
            "base_url": body.base_url or curr.get("base_url", ""),
            "model": body.model or curr.get("model", "")
        }
        llm_client.save_ai_config(new_cfg)
        return llm_client.get_sanitized_config()
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/trade-analyser/test-ai")
def test_ai(body: AITestIn):
    from app import llm_client
    try:
        key = body.api_key.strip() if body.api_key else ""
        if "••••" in key:
            curr = llm_client.load_ai_config()
            key = curr.get("api_key", "")
        return llm_client.test_ai_connection(body.provider, key, body.base_url, body.model)
    except Exception as e:
        return {"success": False, "error": str(e)}

# The Vite dev server proxies /api on port 5174. A Docker build has no dev
# server, so when frontend/dist exists the same API process serves the site.
_DIST = ROOT / "frontend" / "dist"
_INDEX = _DIST / "index.html"
if _INDEX.is_file():
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _assets = _DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (_DIST / full_path).resolve()
        dist_root = _DIST.resolve()
        if full_path and candidate.is_file() and dist_root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_INDEX)

