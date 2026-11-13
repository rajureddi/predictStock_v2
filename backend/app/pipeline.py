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
from app.engine import trader_score, walk_forward_and_forecast, fit_pooled_panel_model
from app.allocate import allocate
from app import regime as regime_mod
from app import surveillance as surv_mod
from app import sectors as sectors_mod
from app import trade_rules
from app import sector_strength as sector_strength_mod

REPORTS = ROOT / "data" / "reports"; REPORTS.mkdir(parents=True, exist_ok=True)
CONFIG = ROOT / "data" / "screen_config.json"
BATCH = 100
MIN_TRADED_VALUE = 15_000_000  # ₹1.5 Crore 20-day median daily traded value (eliminates operator micro-caps)
MIN_ROWS = 120

DEFAULT_SCREEN_RULES = {
    "budget_inr": None,
    "price_cap_mode": "moderate",   # 'no_heavy' (<= ₹2,500) | 'moderate' (<= ₹4,500) | 'allow_heavy' (<= ₹9,500) | 'ultra_heavy' (no cap) | 'custom'
    "min_stock_price": 200.0,
    "max_stock_price": 4500.0,
    "min_profit_inr": 100.0,
    "profit_basis": "auto",         # 'auto' | 'per_share' | 'per_position'
}

PRICE_CAP_LIMITS = {
    "no_heavy": (150.0, 2500.0),
    "moderate": (200.0, 4500.0),
    "allow_heavy": (300.0, 9500.0),
    "ultra_heavy": (100.0, 100000.0),
}

def get_screen_rules():
    cfg = dict(DEFAULT_SCREEN_RULES)
    if CONFIG.exists():
        try:
            saved = json.loads(CONFIG.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update({k: v for k, v in saved.items() if k in DEFAULT_SCREEN_RULES})
        except Exception:
            pass
    mode = cfg.get("price_cap_mode") or "moderate"
    if mode in PRICE_CAP_LIMITS:
        cfg["min_stock_price"], cfg["max_stock_price"] = PRICE_CAP_LIMITS[mode]
    return cfg

def set_screen_rules(updates: dict):
    cfg = get_screen_rules()
    for k, v in (updates or {}).items():
        if k in DEFAULT_SCREEN_RULES:
            cfg[k] = v
    mode = cfg.get("price_cap_mode") or "moderate"
    if mode in PRICE_CAP_LIMITS:
        cfg["min_stock_price"], cfg["max_stock_price"] = PRICE_CAP_LIMITS[mode]
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    return cfg

def get_budget():
    return get_screen_rules().get("budget_inr")

def set_budget(v):
    set_screen_rules({"budget_inr": v})
    return v

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
    try:
        ckpt.write_text(json.dumps({"run_date": date.today().isoformat(), "results": results, "done_batches": sorted(done_batches)}), encoding="utf-8")
    except Exception:
        pass
    for b in range(n_batches):
        if b in done_batches: continue
        batch = tickers[b*BATCH:(b+1)*BATCH]
        data = datafeed.download_batch(batch, period="1y")
        for t, df in data.items():
            if len(df) < MIN_ROWS: continue
            ts = trader_score(df, nifty_close)
            if ts is None: continue
            m = ts["metrics"]
            traded = float((df["Close"] * df["Volume"]).tail(20).median())
            c_lock = surv_mod.has_circuit_lock_risk(df)
            swing_rs = round(max(m["target1"] - m["price"], 1.55 * m["atr"]), 2)
            results.append(dict(yahoo=t, symbol=meta[t]["symbol"], name=meta[t]["name"], exchange=meta[t]["exchange"],
                                isin=meta[t].get("isin") or None,
                                current_price=round(m["price"],2), trader_score=ts["score"], traded_value=round(traded),
                                atr=round(m["atr"], 2), swing_rs=swing_rs,
                                liquid=bool(traded >= MIN_TRADED_VALUE and m["price"] >= 20),
                                circuit_locked=c_lock,
                                delivery_pct=m.get("delivery_pct"),
                                above50=bool(len(df) >= 50 and float(df["Close"].iloc[-1]) > float(df["Close"].tail(50).mean())),
                                rsi=round(m["rsi"],1), ret21_pct=round(m["ret21"]*100,2), reasons=ts["reasons"][:3]))
        done_batches.add(b)
        if b % 2 == 1 or b == n_batches - 1:
            try:
                ckpt.write_text(json.dumps({"run_date": date.today().isoformat(), "results": results, "done_batches": sorted(done_batches)}), encoding="utf-8")
            except Exception:
                pass
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

    # First pass: compute Dalal Street indicators + causal features once per candidate
    scored_map = {}
    feat_frames = {}
    for t, df in data.items():
        if len(df) < 130 or surv_mod.has_circuit_lock_risk(df):
            continue
        try:
            ts = trader_score(df, nifty_close)
            if ts is not None:
                scored_map[t] = (ts, df)
                feat_frames[t] = ts["features"]
        except Exception as e:
            log(f"[stage2] {t} score failed: {e}")

    # Cross-sectional Pooled Panel Model trained strictly on realized historical windows (zero lookahead)
    pooled_model = fit_pooled_panel_model(feat_frames, nifty_close)
    if pooled_model:
        log(f"[stage2] trained cross-sectional Dalal Street pooled model on {pooled_model['n_samples']} 5-day stock-windows")

    evaluated = []
    for t, (ts, df) in scored_map.items():
        try:
            fc = walk_forward_and_forecast(df, nifty_close, pooled_model=pooled_model, prebuilt_features=ts["features"])
        except Exception as e:
            log(f"[stage2] {t} forecast failed: {e}"); continue
        if fc is None:
            continue
        m = ts["metrics"]; c = meta[t]
        pick = dict(symbol=c["symbol"], name=c["name"], exchange=c["exchange"], yahoo=t,
                    isin=c.get("isin"),
                    current_price=round(m["price"],2), trader_score=ts["score"], reasons=ts["reasons"],
                    setup_type=m.get("setup_type"),
                    patterns=m["patterns"], support=m["support"], resistance=m["resistance"],
                    high52=m["high52"], atr=round(m["atr"], 2),
                    stop_loss=m["stop_loss"], breakeven_at=m.get("breakeven_at"), breakeven_stop=m.get("breakeven_stop"),
                    target=m["target1"], target2=m["target2"],
                    risk_reward=m["risk_reward"], rsi=round(m["rsi"],1), adx=round(m["adx"],1),
                    ret3=m.get("ret3"), ret5=m.get("ret5"), vcp_ratio=m.get("vcp_ratio"), clv=m.get("clv"),
                    delivery_pct=m.get("delivery_pct"), delivery_avg5=m.get("delivery_avg5"), dvr=m.get("dvr"),
                    volume_ratio=round(m["vol_ratio"],2),
                    **trade_rules.relative_strength(df["Close"], nifty_close), **fc)
        evaluated.append(pick)
        log(f"[stage2] {t}: score {ts['score']} ({m.get('setup_type')}) pred {fc['predicted_return_pct']}% winP={fc.get('ml_win_prob_pct')}% pass={fc['quality_pass']} acc={fc['backtest']['best_dir_acc']}")

    # Sector labels are filled after this step. The momentum penalty runs once
    # those labels exist, so a bottom-3 sector is not scored before it is known.
    try:
        sec_str = sector_strength_mod.get_sector_strength()
        sector_strength_mod.attach_sector_strength(evaluated, sec_str)
    except Exception as e:
        log(f"[stage2] sector strength attachment failed: {e}")

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

rank_key = trade_rules.rank_key

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

def budget_price_band(budget_inr, want=5):
    """Return (sweet_min_price, max_price) for a user's total portfolio budget across `want` picks."""
    if not budget_inr or budget_inr <= 0:
        return None, None
    b = float(budget_inr)
    slot = b / max(int(want or 5), 1)
    max_price = max(150.0, round(slot * 1.25, 2))
    sweet_min = min(3500.0, max(60.0, round(slot * 0.38, 2)))
    return sweet_min, max_price


def select_picks_for_budget(pool, budget_inr=None, want=5, rules=None):
    """Select the top `want` quality-passed stocks tailored to `budget_inr` and `rules`.
    - Enforces the user's Stock Weight Rule (`no_heavy` <= ₹2,500, `moderate` <= ₹4,500,
      `allow_heavy` <= ₹9,500, `ultra_heavy` <= ₹1,00,000, or `custom` min/max price).
    - Enforces the Minimum Profit Rule (`min_profit_inr`, default >= ₹100).
    - When `budget_inr` is set (e.g. ₹5,000, ₹10,000, ₹25,000), selects 5 stocks in that
      budget's price range so all 5 picks can be bought in whole shares within `budget_inr`."""
    if not pool or want <= 0:
        return []
    rules = rules or get_screen_rules()
    rule_max_px = float(rules.get("max_stock_price") or 4500.0)
    rule_min_px = float(rules.get("min_stock_price") or 100.0)
    min_profit = float(rules.get("min_profit_inr") if rules.get("min_profit_inr") is not None else 100.0)
    profit_basis = str(rules.get("profit_basis") or "auto")

    clean_pool = [dict(p) for p in pool if not (p.get("news") or {}).get("veto")]
    if not clean_pool:
        clean_pool = [dict(p) for p in pool]
    outside = [p for p in clean_pool if not p.get("sector_bottom")]
    if len(outside) >= want:
        clean_pool = outside

    if not budget_inr or float(budget_inr) <= 0:
        # Filter by the active Stock Weight Class Rule (e.g. No Heavy <= ₹2,500 or Moderate <= ₹4,500)
        in_cap = [
            p for p in clean_pool
            if rule_min_px <= float(p.get("current_price") or 0) <= rule_max_px
        ]
        if len(in_cap) < want:
            in_cap = [p for p in clean_pool if float(p.get("current_price") or 0) <= rule_max_px]
        if not in_cap:
            in_cap = clean_pool

        with_profit = [
            p for p in in_cap
            if (float(p.get("predicted_price") or 0) - float(p.get("current_price") or 0)) >= min_profit
        ]
        if len(with_profit) >= want:
            base = with_profit
        else:
            # Rank those meeting min_profit first, then closest to min_profit inside the weight cap
            base = in_cap
        base.sort(key=lambda p: (
            0 if (float(p.get("predicted_price") or 0) - float(p.get("current_price") or 0)) >= min_profit else 1,
            0 if float(p.get("current_price") or 0) <= rule_max_px else 1,
            rank_key(p),
        ))
        capped, _ = sectors_mod.apply_sector_cap(base, want=want)
        return capped[:want]

    b = float(budget_inr)
    slot = b / max(want, 1)
    sweet_min, max_price = budget_price_band(b, want=want)
    eff_max_price = min(max_price, rule_max_px)
    eff_min_price = min(sweet_min, eff_max_price * 0.5)
    affordable = [p for p in clean_pool if 0 < float(p.get("current_price") or 0) <= eff_max_price]
    if len(affordable) < want:
        affordable = [p for p in clean_pool if 0 < float(p.get("current_price") or 0) <= min(rule_max_px, max(max_price * 1.35, b * 0.45))]
    if len(affordable) < want:
        affordable = [p for p in clean_pool if 0 < float(p.get("current_price") or 0) <= max(max_price * 1.35, b * 0.45)]
    if not affordable:
        affordable = sorted(clean_pool, key=lambda p: float(p.get("current_price") or 999999))[:want]

    def _budget_rank(p):
        px = float(p.get("current_price") or 1.0)
        pred_px = float(p.get("predicted_price") or px)
        gain_sh = max(0.0, pred_px - px)
        in_sweet = 0 if (eff_min_price <= px <= eff_max_price) else 1
        est_shares = max(1, int(slot // px)) if px <= slot else 1
        slot_profit_rs = est_shares * gain_sh
        if profit_basis == "per_share":
            meets_min_prof = 0 if gain_sh >= min_profit else 1
        elif profit_basis == "per_position":
            meets_min_prof = 0 if slot_profit_rs >= min_profit else 1
        else:
            meets_min_prof = 0 if (gain_sh >= min_profit or slot_profit_rs >= min_profit) else 1
        return (
            meets_min_prof,
            in_sweet,
            0 if gain_sh >= min_profit else 1,
            -round(slot_profit_rs / max(slot, 1.0) * 100.0, 1),
            rank_key(p),
        )

    affordable.sort(key=_budget_rank)
    capped, _ = sectors_mod.apply_sector_cap(affordable, want=len(affordable))

    # Greedily pick `want` stocks ensuring the sum of 1 whole share each stays <= budget_inr
    selected = []
    running_min_cost = 0.0
    for cand in capped:
        if len(selected) >= want:
            break
        px = float(cand.get("current_price") or 0)
        remaining_slots = max(0, (want - 1) - len(selected))
        min_reserve = remaining_slots * min(150.0, slot * 0.30)
        if running_min_cost + px + min_reserve <= b or len(selected) == 0:
            selected.append(cand)
            running_min_cost += px
    if len(selected) < want:
        used = {p.get("symbol") for p in selected}
        for cand in sorted(affordable, key=lambda x: float(x.get("current_price") or 999999)):
            if len(selected) >= want:
                break
            if cand.get("symbol") in used:
                continue
            px = float(cand.get("current_price") or 0)
            if running_min_cost + px <= b:
                selected.append(cand)
                used.add(cand.get("symbol"))
                running_min_cost += px
    return selected[:want]


def _select_stratified_stage2_candidates(liquid, limit=150):
    """Build a 150-stock Stage-2 pool prioritizing accessible mid-priced ₹100+ swing
    leaders (₹1,100–₹4,500) alongside ₹5k–₹10k budget leaders (₹300–₹1,100)."""
    by_score = lambda r: (
        -r["trader_score"],
        0 if r.get("exchange") == "NSE" else 1,
        -r.get("traded_value", 0),
    )
    # Tier 1: Accessible Mid-Priced ₹100+ Swing Leaders (₹1,100 <= price <= ₹4,500, swing_rs >= 85)
    tier_mid_100 = sorted(
        [r for r in liquid if 1100.0 <= float(r.get("current_price") or 0) <= 4500.0 and (r.get("swing_rs") or 0) >= 85.0],
        key=by_score,
    )
    used = set()
    top = []
    for r in tier_mid_100[:85]:
        top.append(r)
        used.add(r["yahoo"])

    # Tier 2: ₹5k - ₹10k Budget Leaders (₹350 <= price < ₹1,100)
    tier_compact = sorted(
        [r for r in liquid if r["yahoo"] not in used and 350.0 <= float(r.get("current_price") or 0) < 1100.0],
        key=lambda r: (0 if (r.get("swing_rs") or 0) >= 35.0 else 1, *by_score(r)),
    )
    for r in tier_compact[:45]:
        top.append(r)
        used.add(r["yahoo"])

    # Tier 3: Remaining top-scored liquid setups
    if len(top) < limit:
        for r in sorted(liquid, key=by_score):
            if len(top) >= limit:
                break
            if r["yahoo"] not in used:
                top.append(r)
                used.add(r["yahoo"])
    return top[:limit]


def run_pipeline(log=print, fresh: bool = False):
    run_date = date.today()
    if fresh:
        (REPORTS / "stage1_checkpoint.json").unlink(missing_ok=True)
    uni = univ_mod.load_universe()
    log(f"Universe: {uni['counts']} (fresh={fresh})")
    try: bhavcopy.top_up(log=log)
    except Exception as e: log(f"[bhavcopy] top-up error: {e}")
    s1 = stage1(uni, checkpoint=not fresh, log=log)
    (REPORTS / "stage1_checkpoint.json").unlink(missing_ok=True)
    liquid = [r for r in s1 if r["liquid"]]
    liquid.sort(key=lambda r: (
        0 if (r.get("swing_rs") or 0) >= 100.0 else 1,
        -r["trader_score"],
        0 if r.get("exchange") == "NSE" else 1,
        -r.get("traded_value", 0),
    ))
    liquid, dup_s1 = dedupe_by_isin(liquid)
    if dup_s1: log(f"[stage1] dropped {len(dup_s1)} duplicate cross-listings before stage 2")
    # Market regime gate (NIFTY vs 50/200-DMA) + India VIX sizing
    regime = regime_mod.get_market_regime(log=log)
    breadth = round(sum(1 for r in liquid if r.get("above50")) / len(liquid) * 100, 1) if len(liquid) >= 20 else None
    _nf5 = datafeed.download_batch(["^NSEI"], period="1mo").get("^NSEI")
    nifty_ret5 = float((_nf5["Close"].iloc[-1] / _nf5["Close"].iloc[-6] - 1.0) * 100.0) if (_nf5 is not None and len(_nf5) >= 6) else None
    # Select 5 high-conviction stocks whenever the market is not in a total breadth washout (<24%);
    # bear/cautious regimes control risk via cash_pct (50% cash reserve) and size_mult rather than starving picks.
    if breadth is not None and breadth < trade_rules.BREADTH_NO_TRADE:
        want = 0
    elif nifty_ret5 is not None and nifty_ret5 < -4.0 and (breadth or 50) < 35.0:
        want = 0
    else:
        want = 5
    regime["max_picks"] = want
    log(f"[breadth] {breadth}% of liquid stocks above 50-DMA (regime={regime.get('regime')}) -> target picks {want}")
    # Surveillance hard veto (ASM / GSM / ESM / trade-to-trade / circuit locks) BEFORE the expensive stage 2
    series_map = {(l["symbol"], l["exchange"]): l.get("series") for l in uni["listings"]}
    liquid, surveillance_vetoed = surv_mod.apply_surveillance_veto(liquid, series_map=series_map, log=log)
    if surveillance_vetoed: log(f"[surveillance] vetoed {len(surveillance_vetoed)} listings before stage 2")
    top = _select_stratified_stage2_candidates(liquid, limit=150)
    # For any remaining BSE candidates, check if universe has an equivalent primary NSE listing by ISIN
    isin_to_nse = {l["isin"]: l["yahoo"] for l in uni.get("listings", []) if l.get("isin") and l.get("exchange") == "NSE" and l.get("yahoo")}
    for c in top:
        if c.get("exchange") == "BSE" and c.get("isin") in isin_to_nse:
            c["yahoo"] = isin_to_nse[c["isin"]]
    log(f"[stage1] with-data={len(s1)} liquid={len(liquid)} -> stage2={len(top)}")
    evaluated = stage2(top, log=log)
    f_cache = fundamentals_mod._load_cache()
    s_cache = sectors_mod._load()
    for e in evaluated:
        yh = e.get("yahoo") or f"{e['symbol']}.NS"
        f_entry = f_cache.get(yh) or {}
        e["fundamentals"] = f_entry.get("data") if isinstance(f_entry, dict) else None
        s_entry = s_cache.get(yh) or {}
        e["sector"] = s_entry.get("sector") or "Unclassified"
        e["industry"] = s_entry.get("industry")
    try:
        sector_strength = sector_strength_mod.get_sector_strength()
    except Exception as e:
        log(f"[sector-strength] unavailable: {e}"); sector_strength = {"sectors": []}
    sector_strength_mod.attach_sector_strength(evaluated, sector_strength)
    # VIX stop widening is applied before the simulation so the Monte Carlo tests the stop we will actually use
    for e in evaluated: regime_mod.apply_stop_widen(e, regime.get("stop_widen", 1.0))
    # Pre-gate without simulation (cheap), then simulate survivors and apply the full gate.
    # No fallbacks: if nothing passes, the week publishes zero picks.
    good = [e for e in evaluated if not trade_rules.gate_failures(e)] if want > 0 else []
    if good:
        fundamentals_mod.attach_fundamentals(good, log=log)
        sectors_mod.attach_sectors(good, log=log)
        sector_strength_mod.apply_momentum_penalty(good, sector_strength)
    sim_rejected = []
    try:
        from app import simulation
        log(f"[pipeline] running Time Machine simulations across {len(good)} candidate stocks...")
        for c in good:
            c["simulation"] = simulation.simulate_pick(c, replays=1000)
            c["orb"] = simulation.check_orb_status(c)
    except Exception as e:
        log(f"[pipeline] simulation stress-test skipped: {e}")
    passed = []
    for c in good:
        why = trade_rules.gate_failures(c)
        if why:
            c["gate_reasons"] = why
            sim_rejected.append(c)
            log(f"[gate] REJECTED {c['symbol']}: {'; '.join(why)}")
        else:
            passed.append(c)
    good = passed

    good.sort(key=rank_key)
    good, dup_final = dedupe_by_isin(good)
    if dup_final: log(f"[ranking] dropped duplicate cross-listings: {[p['symbol'] for p in dup_final]}")
    pool, demoted = apply_red_flag_demotion(good, keep=want)
    if demoted: log(f"[fundamentals] red-flag demoted: {[p['symbol'] for p in demoted]}")
    # Earnings inside the holding window: skip when enough clean picks exist, else flag
    pool, earnings_skipped = surv_mod.apply_earnings_filter(pool, run_date.isoformat(), target_date_for(run_date), keep=want, log=log)
    sectors_mod.attach_sectors(pool, log=log)
    # News-check up to 30 top candidates across all budget tiers so dynamic budget switching has verified news
    candidate_pool, vetoed = finalize_with_news(pool, log=log, want=min(len(pool), 30), max_checks=35)
    candidate_pool = [p for p in candidate_pool if not (p.get("news") or {}).get("veto")]
    for p in candidate_pool:
        p.pop("yahoo", None)
        p["trade_plan"] = trade_rules.trade_plan(p, run_date)

    budget = get_budget()
    sector_capped = []
    picks = select_picks_for_budget(candidate_pool, budget_inr=budget, want=want)
    alloc = allocate(picks, budget, size_mult=regime.get("size_mult", 1.0), cash_pct=regime.get("cash_pct", 0.0), budget_mode=True) if budget else None
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
                                    liquid=len(liquid), stage2=len(evaluated), quality_passed=len(candidate_pool)),
                  picks=picks, candidate_pool=candidate_pool, allocation=alloc,
                  market_regime=regime,
                  market_breadth_pct=breadth,
                  sector_strength=sector_strength.get("sectors", []),
                  no_trade=len(picks) == 0,
                  no_trade_reason=(None if picks else
                                   (f"Market breadth {breadth}% is below {trade_rules.BREADTH_NO_TRADE:.0f}% - stay in cash this week."
                                    if want == 0 else "No stock passed every trade rule this week - stay in cash.")),
                  vetoed=vetoed,
                  surveillance_vetoed=surveillance_vetoed,
                  earnings_skipped=[dict(symbol=p["symbol"], name=p["name"], exchange=p["exchange"],
                                         current_price=p.get("current_price"), earnings_date=p.get("earnings_date"),
                                         predicted_return_pct=p.get("predicted_return_pct")) for p in earnings_skipped],
                  sector_capped=sector_capped,
                  simulation_rejected=[dict(symbol=p["symbol"], name=p["name"], exchange=p["exchange"],
                                             reasons=p.get("gate_reasons", []),
                                             risk=(p.get("simulation") or {}).get("loss_probability_pct", 0),
                                             win_odds=(p.get("simulation") or {}).get("win_probability_pct", 0)) for p in sim_rejected],
                  red_flag_demoted=[dict(symbol=p["symbol"], name=p["name"], exchange=p["exchange"],
                                         flags=(p.get("fundamentals") or {}).get("flags", []),
                                         fundamentals=p.get("fundamentals")) for p in demoted],
                  stage1_top50=[dict(symbol=r["symbol"], name=r["name"], exchange=r["exchange"], current_price=r["current_price"],
                                     trader_score=r["trader_score"], delivery_pct=r.get("delivery_pct"),
                                     rsi=r["rsi"], ret21_pct=r["ret21_pct"], reasons=r["reasons"]) for r in liquid[:50]],
                  evaluated_count=len(evaluated))
    from app import report_store
    report_store.save_report(report)
    # Single working copy for the live picks page. Each day's history is in reports.db.
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"Done. Picks: {[p['symbol'] for p in picks]}")
    return report

if __name__ == "__main__":
    run_pipeline()
