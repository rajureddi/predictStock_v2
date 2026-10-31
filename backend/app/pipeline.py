"""Weekly pipeline: stage1 screen ALL listings -> stage2 deep ML evaluation
of top ~150 -> final 5-7 quality-passed picks. Resumable stage 1 via checkpoint."""
import json, math, sys, time
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import universe as univ_mod, datafeed, bhavcopy
from app import fundamentals as fundamentals_mod
from app import news as news_mod
from app.engine import trader_score, walk_forward_and_forecast
from app.allocate import allocate
from app import regime as regime_mod
from app import surveillance as surv_mod
from app import sectors as sectors_mod

REPORTS = ROOT / "data" / "reports"; REPORTS.mkdir(parents=True, exist_ok=True)
CONFIG = ROOT / "data" / "screen_config.json"
BATCH = 100
MIN_TRADED_VALUE = 5_000_00 * 10  # ₹50 lakh avg daily traded value (5,000,000)
MIN_ROWS = 120

def get_budget():
    if CONFIG.exists():
        try: return json.loads(CONFIG.read_text(encoding="utf-8")).get("budget_inr")
        except Exception: return None
    return None

def set_budget(v):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({"budget_inr": v}, indent=1), encoding="utf-8"); return v

def target_date_for(run_date):
    return (run_date + timedelta(days=7)).isoformat()

def stage1(universe, checkpoint=True, log=print):
    ckpt = REPORTS / "stage1_checkpoint.json"
    results, done_batches = [], set()
    if checkpoint and ckpt.exists():
        try:
            saved = json.loads(ckpt.read_text(encoding="utf-8"))
            if saved.get("run_date") and saved.get("run_date") != date.today().isoformat(): raise ValueError("stale checkpoint")
            results = saved["results"]; done_batches = set(saved["done_batches"])
            log(f"[stage1] resuming: {len(results)} symbols, {len(done_batches)} batches done")
        except Exception: pass
    tickers = [l["yahoo"] for l in universe["listings"]]
    meta = {l["yahoo"]: l for l in universe["listings"]}
    nifty = datafeed.download_batch(["^NSEI"], period="1y").get("^NSEI")
    nifty_close = nifty["Close"] if nifty is not None else None
    n_batches = math.ceil(len(tickers)/BATCH)
    for b in range(n_batches):
        if b in done_batches: continue
        batch = tickers[b*BATCH:(b+1)*BATCH]
        data = datafeed.download_batch(batch, period="1y")
        for t, df in data.items():
            if len(df) < MIN_ROWS: continue
            ts = trader_score(df, nifty_close)
            if ts is None: continue
            m = ts["metrics"]; avg_vol = float(df["Volume"].tail(20).mean())
            traded = m["price"]*avg_vol
            results.append(dict(yahoo=t, symbol=meta[t]["symbol"], name=meta[t]["name"], exchange=meta[t]["exchange"],
                                isin=meta[t].get("isin") or None,
                                current_price=round(m["price"],2), trader_score=ts["score"], traded_value=round(traded),
                                liquid=bool(traded >= MIN_TRADED_VALUE and m["price"] >= 5),
                                delivery_pct=m.get("delivery_pct"),
                                rsi=round(m["rsi"],1), ret21_pct=round(m["ret21"]*100,2), reasons=ts["reasons"][:3]))
        done_batches.add(b)
        if checkpoint:
            ckpt.write_text(json.dumps({"run_date": date.today().isoformat(), "results": results, "done_batches": sorted(done_batches)}), encoding="utf-8")
        log(f"[stage1] batch {b+1}/{n_batches}: total with data {len(results)}")
    return results

def stage2(candidates, log=print):
    tickers = [c["yahoo"] for c in candidates]
    data = {}
    for i in range(0, len(tickers), 50):
        data.update(datafeed.download_batch(tickers[i:i+50], period="2y"))
        log(f"[stage2] downloaded {len(data)}/{len(tickers)}")
    nifty = datafeed.download_batch(["^NSEI"], period="2y").get("^NSEI")
    nifty_close = nifty["Close"] if nifty is not None else None
    meta = {c["yahoo"]: c for c in candidates}
    evaluated = []
    for t, df in data.items():
        if len(df) < 150: continue
        try:
            ts = trader_score(df, nifty_close)
            fc = walk_forward_and_forecast(df, nifty_close)
        except Exception as e:
            log(f"[stage2] {t} failed: {e}"); continue
        if ts is None or fc is None: continue
        m = ts["metrics"]; c = meta[t]
        pick = dict(symbol=c["symbol"], name=c["name"], exchange=c["exchange"], yahoo=t,
                    isin=c.get("isin"),
                    current_price=round(m["price"],2), trader_score=ts["score"], reasons=ts["reasons"],
                    patterns=m["patterns"], support=m["support"], resistance=m["resistance"],
                    high52=m["high52"], stop_loss=m["stop_loss"], target=m["target1"], target2=m["target2"],
                    risk_reward=m["risk_reward"], rsi=round(m["rsi"],1), adx=round(m["adx"],1),
                    delivery_pct=m.get("delivery_pct"), delivery_avg5=m.get("delivery_avg5"),
                    volume_ratio=round(m["vol_ratio"],2), **fc)
        evaluated.append(pick)
        log(f"[stage2] {t}: score {ts['score']} pred {fc['predicted_return_pct']}% pass={fc['quality_pass']} acc={fc['backtest']['best_dir_acc']}")
    return evaluated

def dedupe_by_isin(ranked):
    """The same company often lists on both exchanges (same ISIN). Keep
    only one listing, strictly prioritizing primary NSE listings (.NS)
    over BSE numerical scrips (.BO) for cleaner data and fast downloads.
    Returns (kept, dropped)."""
    by_key = {}
    for p in ranked:
        key = p.get("isin") or p.get("symbol") or p.get("yahoo")
        if key not in by_key:
            by_key[key] = p
        else:
            existing = by_key[key]
            # Prioritize NSE listing over BSE
            if p.get("exchange") == "NSE" and existing.get("exchange") != "NSE":
                by_key[key] = p
            elif p.get("exchange") == existing.get("exchange") and p.get("trader_score", 0) > existing.get("trader_score", 0):
                by_key[key] = p
    kept_ids = {id(v) for v in by_key.values()}
    kept = [p for p in ranked if id(p) in kept_ids]
    dropped = [p for p in ranked if id(p) not in kept_ids]
    return kept, dropped

def rank_key(e):
    """Final ranking: incorporates Trader Score, Time Machine Expected Payoff & Win Odds,
    Predicted Return, Backtest Accuracy, Risk-Reward, and Fundamentals Quality."""
    fs = (e.get("fundamentals") or {}).get("score")
    fs = 50.0 if fs is None else fs
    sim = e.get("simulation") or {}
    sim_win = sim.get("win_probability_pct", 50.0)
    avg_r = sim.get("avg_R", 0.0) or 0.0
    rr = e.get("risk_reward") or 1.0
    rsi = e.get("rsi") or 55.0
    ob_pen = max(0.0, (rsi - 78.0) * 1.8) if rsi > 78.0 else 0.0
    return -(e["trader_score"]*0.45 + min(sim_win, 100)*0.20 + avg_r*12.0 + (rr - 1.0)*4.0
             + min(e["predicted_return_pct"], 8)*1.6
             + e["backtest"]["best_dir_acc"]*0.15 + (fs - 50)*0.05 - ob_pen)

def apply_red_flag_demotion(ranked, keep=7):
    """Severe red flag (D/E>3 AND earnings shrinking): dropped from the
    selection pool when at least `keep` clean picks exist. Returns
    (pool, demoted) — demoted picks stay visible in the report."""
    clean = [p for p in ranked if not fundamentals_mod.severe_red_flag(p.get("fundamentals"))]
    flagged = [p for p in ranked if fundamentals_mod.severe_red_flag(p.get("fundamentals"))]
    if flagged and len(clean) >= keep:
        return clean, flagged
    return ranked, []

def finalize_with_news(ranked, log=print, want=7, max_checks=25):
    """News-check ranked candidates in order until `want` clean picks are
    collected. Vetoed candidates are skipped (and reported); if the pool
    runs out before `want` clean picks, vetoed ones fill the remaining
    slots — still carrying their veto flag for the UI."""
    for c in ranked: c.setdefault("news", None)
    picks, vetoed = [], []
    checked = 0
    for cand in ranked:
        if len(picks) >= want or checked >= max_checks: break
        checked += 1
        n = news_mod.get_news(cand, log=log)
        cand["news"] = n
        if n and n.get("veto"):
            vetoed.append(dict(symbol=cand["symbol"], name=cand["name"], exchange=cand["exchange"],
                               current_price=cand["current_price"],
                               predicted_return_pct=cand["predicted_return_pct"],
                               reason=n.get("veto_reason"), news=n, _cand=cand))
            log(f"[news] VETO {cand['symbol']}: {n.get('veto_reason')}")
            continue
        picks.append(cand)
    if len(picks) < want:
        for v in vetoed:
            if len(picks) >= want: break
            picks.append(v["_cand"])
    picked_ids = {id(p) for p in picks}
    vetoed_out = [v for v in vetoed if id(v["_cand"]) not in picked_ids]
    for v in vetoed_out: v.pop("_cand", None)
    return picks, vetoed_out

def run_pipeline(log=print):
    run_date = date.today()
    uni = univ_mod.load_universe()
    log(f"Universe: {uni['counts']}")
    try: bhavcopy.top_up(log=log)
    except Exception as e: log(f"[bhavcopy] top-up error: {e}")
    s1 = stage1(uni, log=log)
    (REPORTS / "stage1_checkpoint.json").unlink(missing_ok=True)
    liquid = [r for r in s1 if r["liquid"]]
    liquid.sort(key=lambda r: (-r["trader_score"], 0 if r.get("exchange") == "NSE" else 1, -r.get("traded_value", 0)))
    liquid, dup_s1 = dedupe_by_isin(liquid)
    if dup_s1: log(f"[stage1] dropped {len(dup_s1)} duplicate cross-listings before stage 2")
    # Market regime gate (NIFTY vs 50/200-DMA) + India VIX sizing
    regime = regime_mod.get_market_regime(log=log)
    want = int(regime.get("max_picks") or 7)
    # Surveillance hard veto (ASM / GSM / trade-to-trade) BEFORE the expensive stage 2
    series_map = {(l["symbol"], l["exchange"]): l.get("series") for l in uni["listings"]}
    liquid, surveillance_vetoed = surv_mod.apply_surveillance_veto(liquid, series_map=series_map, log=log)
    if surveillance_vetoed: log(f"[surveillance] vetoed {len(surveillance_vetoed)} listings before stage 2")
    top = liquid[:150]
    # For any remaining BSE candidates, check if universe has an equivalent primary NSE listing by ISIN
    isin_to_nse = {l["isin"]: l["yahoo"] for l in uni.get("listings", []) if l.get("isin") and l.get("exchange") == "NSE" and l.get("yahoo")}
    for c in top:
        if c.get("exchange") == "BSE" and c.get("isin") in isin_to_nse:
            c["yahoo"] = isin_to_nse[c["isin"]]
    log(f"[stage1] with-data={len(s1)} liquid={len(liquid)} -> stage2={len(top)}")
    evaluated = stage2(top, log=log)
    fundamentals_mod.attach_fundamentals(evaluated, log=log)
    # VIX stop widening is applied before the simulation so the Monte Carlo tests the stop we will actually use
    for e in evaluated: regime_mod.apply_stop_widen(e, regime.get("stop_widen", 1.0))
    good = [e for e in evaluated if e["quality_pass"] and e["predicted_return_pct"] > 0 and (e.get("rsi") or 50) <= 80.0 and (e.get("risk_reward") or 1.0) >= 1.15]
    if len(good) < 7:
        good = [e for e in evaluated if e["quality_pass"] and e["predicted_return_pct"] > 0]
    
    # Stress-Test Gate: Run 5-Day High/Low Time Machine simulations on candidate pool
    sim_rejected = []
    try:
        from app import simulation
        log(f"[pipeline] running Time Machine simulations across {len(good)} candidate stocks...")
        for c in good:
            c["simulation"] = simulation.simulate_pick(c, replays=1000)
            c["orb"] = simulation.check_orb_status(c)
        clean_pool = []
        for c in good:
            sim = c.get("simulation")
            if sim and (sim.get("avg_R", 0) < -0.05 or (sim.get("avg_R", 0) < 0 and sim.get("loss_probability_pct", 0) > sim.get("win_probability_pct", 0))):
                sim_rejected.append(c)
                log(f"[simulation-gate] REJECTED {c['symbol']}: avg_R={sim.get('avg_R')} Stop risk ({sim['loss_probability_pct']}%) vs Win odds ({sim['win_probability_pct']}%)")
            else:
                clean_pool.append(c)
        if len(clean_pool) >= 7:
            good = clean_pool
    except Exception as e:
        log(f"[pipeline] simulation stress-test skipped: {e}")

    good.sort(key=rank_key)
    good, dup_final = dedupe_by_isin(good)
    if dup_final: log(f"[ranking] dropped duplicate cross-listings: {[p['symbol'] for p in dup_final]}")
    pool, demoted = apply_red_flag_demotion(good, keep=want)
    if demoted: log(f"[fundamentals] red-flag demoted: {[p['symbol'] for p in demoted]}")
    # Earnings inside the holding window: skip when enough clean picks exist, else flag
    pool, earnings_skipped = surv_mod.apply_earnings_filter(pool, run_date.isoformat(), target_date_for(run_date), keep=want, log=log)
    # Sector concentration cap: max 2 per sector, capped names fill only a short pool
    sectors_mod.attach_sectors(pool, log=log)
    pool, sector_capped = sectors_mod.apply_sector_cap(pool, want=want)
    if sector_capped: log(f"[sectors] capped: {[p['symbol'] for p in sector_capped]}")
    picks, vetoed = finalize_with_news(pool, log=log, want=want)
    # strip internal helpers
    for p in picks: p.pop("yahoo", None)
    budget = get_budget()
    alloc = allocate(picks, budget, size_mult=regime.get("size_mult", 1.0), cash_pct=regime.get("cash_pct", 0.0)) if budget else None
    if alloc:
        for i, p in enumerate(picks):
            a = alloc["allocations"][i] if i < len(alloc["allocations"]) else None
            if a: p.update(shares=a["shares"], invested=a["invested"], expected_value=a["expected_value"], expected_profit=a["expected_profit"], risk_inr=a.get("risk_inr"))
    _nf = datafeed.download_batch(["^NSEI"], period="5d").get("^NSEI")
    data_asof = str(_nf.index[-1].date()) if _nf is not None and len(_nf) else None
    if not data_asof:
        try:
            meta = json.loads((ROOT / "data" / "history" / "panel_meta.json").read_text(encoding="utf-8"))
            lasts = [v.get("last") for v in meta.values() if v.get("last")]
            data_asof = max(lasts) if lasts else None
        except Exception: pass
    report = dict(product="MarketMind Pro", version="2.0", run_date=run_date.isoformat(), data_as_of=data_asof,
                  target_date=target_date_for(run_date), horizon="7 calendar days (5 trading days)",
                  universe_counts=uni["counts"],
                  stage_counts=dict(universe=uni["counts"]["total"], with_data=len(s1),
                                    nse_with_data=sum(1 for r in s1 if r["exchange"] == "NSE"),
                                    bse_with_data=sum(1 for r in s1 if r["exchange"] == "BSE"),
                                    liquid=len(liquid), stage2=len(evaluated), quality_passed=len(good)),
                  picks=picks, allocation=alloc,
                  market_regime=regime,
                  vetoed=vetoed,
                  surveillance_vetoed=surveillance_vetoed,
                  earnings_skipped=[dict(symbol=p["symbol"], name=p["name"], exchange=p["exchange"],
                                         current_price=p.get("current_price"), earnings_date=p.get("earnings_date"),
                                         predicted_return_pct=p.get("predicted_return_pct")) for p in earnings_skipped],
                  sector_capped=sector_capped,
                  simulation_rejected=[dict(symbol=p["symbol"], name=p["name"], exchange=p["exchange"],
                                             risk=(p.get("simulation") or {}).get("loss_probability_pct", 0),
                                             win_odds=(p.get("simulation") or {}).get("win_probability_pct", 0)) for p in sim_rejected],
                  red_flag_demoted=[dict(symbol=p["symbol"], name=p["name"], exchange=p["exchange"],
                                         flags=(p.get("fundamentals") or {}).get("flags", []),
                                         fundamentals=p.get("fundamentals")) for p in demoted],
                  stage1_top50=[dict(symbol=r["symbol"], name=r["name"], exchange=r["exchange"], current_price=r["current_price"],
                                     trader_score=r["trader_score"], delivery_pct=r.get("delivery_pct"),
                                     rsi=r["rsi"], ret21_pct=r["ret21_pct"], reasons=r["reasons"]) for r in liquid[:50]],
                  evaluated_count=len(evaluated))
    (REPORTS / f"report-{run_date.isoformat()}.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"Done. Picks: {[p['symbol'] for p in picks]}")
    return report

if __name__ == "__main__":
    run_pipeline()
