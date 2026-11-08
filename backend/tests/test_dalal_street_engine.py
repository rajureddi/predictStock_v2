"""Unit tests for the Dalal Street Institutional 5-Day Prediction Engine upgrades:
- Continuous candle micro-geometry & zero-lookahead Triple-Barrier forward labels
- Delivery Volume Surge (DVR) vs. Intraday Operator Churn penalty
- Controlled Stage-2 Pullback Reversal vs. 3-5d Short-Horizon Chase penalty
- Realistic 5-day ATR target envelope + 'Mooli Salamat' breakeven stop-trailing
- Circuit-lock trap detection & ESM surveillance veto
- Cross-sectional Pooled Panel Classifier + 5-Day Synthetic Candle outputs
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import backtest as bt
from app import simulation as sim_mod
from app import trade_rules
from app.engine import (
    FEATURES,
    HORIZON,
    build_features,
    fit_pooled_panel_model,
    predict_pooled_panel,
    trader_score,
    walk_forward_and_forecast,
)
from app.surveillance import has_circuit_lock_risk, surveillance_flags


def _stage2_frame(n=260, seed=19):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0018, 0.011, n)
    close = 200.0 * np.exp(np.cumsum(rets))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) * 1.008
    low = np.minimum(open_, close) * 0.992
    vol = rng.integers(300_000, 900_000, n).astype(float)
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )


def test_forward_labels_strictly_leak_free_and_candle_features_present():
    df = _stage2_frame(240)
    d = build_features(df)
    clean = d.dropna(subset=FEATURES)
    assert clean.index[-1] == df.index[-1]
    for col in ("TARGET", "TB_WIN", "FWD_HIGH_ATR", "FWD_LOW_ATR"):
        assert clean[col].iloc[-HORIZON:].isna().all()
        assert not clean[col].iloc[:-HORIZON].isna().any()
    for col in ("CLV", "BODY_ATR", "LWICK_ATR", "UWICK_ATR", "VCP_RATIO", "RSI2", "DVR", "HAS_DELIV"):
        assert col in clean.columns


def test_operator_churn_penalised_and_delivery_surge_rewarded():
    base_df = _stage2_frame(160)
    last_idx = base_df.index[-1]
    prev_c = float(base_df["Close"].iloc[-2])
    base_df.loc[last_idx, "Open"] = prev_c
    base_df.loc[last_idx, "Close"] = prev_c * 1.03
    base_df.loc[last_idx, "High"] = prev_c * 1.032
    base_df.loc[last_idx, "Low"] = prev_c * 0.998
    base_df["Volume"] = 500_000.0
    base_df.loc[last_idx, "Volume"] = 1_200_000.0  # 2.4x volume spike

    churn = base_df.copy()
    churn["DelivPer"] = 14.0
    churn["DelivQty"] = 70_000.0

    surge = base_df.copy()
    surge["DelivPer"] = 64.0
    surge["DelivQty"] = 250_000.0
    surge.loc[last_idx, "DelivQty"] = 768_000.0  # >3x 20d delivery surge

    ts_base = trader_score(base_df)
    ts_churn = trader_score(churn)
    ts_surge = trader_score(surge)
    assert ts_churn["score"] == max(0.0, ts_base["score"] - 8.0)
    assert ts_surge["score"] == min(100.0, ts_base["score"] + 7.0)
    assert any("operator churn" in r.lower() for r in ts_churn["reasons"])
    assert any("delivery volume surge" in r.lower() for r in ts_surge["reasons"])


def test_realistic_5d_atr_target_and_chase_penalty():
    df = _stage2_frame(200)
    ts = trader_score(df)
    m = ts["metrics"]
    atr = m["atr"]
    # 5-day Target 1 must be realistic (1.15x - 1.90x ATR), never 2.5x - 3.8x ATR
    tgt_atr = (m["target1"] - m["price"]) / atr
    assert 1.15 <= tgt_atr <= 1.90
    assert m["breakeven_at"] > m["price"]
    assert m["breakeven_stop"] > m["price"]

    # 3-day +11% vertical spike gets penalized vs unextended frame
    chased = df.copy()
    chased.iloc[-3:, chased.columns.get_loc("Close")] *= np.array([1.035, 1.072, 1.115])
    chased["High"] = np.maximum(chased["High"], chased["Close"] * 1.003)
    ts_chase = trader_score(chased)
    assert ts_chase["score"] < ts["score"]


def test_mooli_salamat_breakeven_trail_zero_intrabar_lookahead():
    idx = pd.bdate_range("2026-02-02", periods=5)
    # Bar 1 rallies to 108 (>= breakeven_at 107.5) without hitting target 114; Bar 2 reverses down to 97
    bars = pd.DataFrame(
        {
            "Open": [100.5, 106.0, 98.0, 97.0, 96.0],
            "High": [108.5, 106.5, 99.0, 98.0, 97.0],
            "Low": [99.8, 97.0, 96.0, 95.0, 94.0],
            "Close": [107.0, 98.0, 97.0, 96.0, 95.0],
        },
        index=idx,
    )
    # Without breakeven trail -> loses on Day 4 at stop=95 (or Day 5 at 95)
    ex_raw = bt.simulate_exit(bars, entry=100.0, stop=95.5, target=114.0)
    assert ex_raw["exit"] <= 95.5
    # With Mooli Salamat -> locks in +0.42% on Bar 2 reversal!
    ex_be = bt.simulate_exit(
        bars, entry=100.0, stop=95.5, target=114.0, breakeven_at=107.5, breakeven_stop=100.42
    )
    assert ex_be["reason"] == "breakeven" and abs(ex_be["exit"] - 100.42) < 1e-6 and ex_be["bars_held"] == 2

    # Zero intrabar lookahead: if Bar 1 touches BOTH breakeven_at (108.5) AND initial stop (95.5), it MUST stop out!
    bars_ambig = bars.copy()
    bars_ambig.iloc[0, bars_ambig.columns.get_loc("Low")] = 95.0
    ex_ambig = bt.simulate_exit(
        bars_ambig, entry=100.0, stop=95.5, target=114.0, breakeven_at=107.5, breakeven_stop=100.42
    )
    assert ex_ambig["reason"] == "stop" and ex_ambig["exit"] == 95.5


def test_circuit_lock_risk_and_esm_flag():
    clean_df = _stage2_frame(60)
    assert has_circuit_lock_risk(clean_df) is False

    locked_df = clean_df.copy()
    prev_c = float(locked_df["Close"].iloc[-2])
    lim_px = round(prev_c * 0.95, 2)  # 5% lower-circuit lock bar (O=H=L=C)
    for col in ("Open", "High", "Low", "Close"):
        locked_df.iloc[-1, locked_df.columns.get_loc(col)] = lim_px
    assert has_circuit_lock_risk(locked_df) is True

    flags = surveillance_flags("OPER", "NSE", "ST", dict(asm=set(), gsm=set(), esm={"OPER"}))
    assert "ESM" in flags and "T2T" in flags


def test_pooled_panel_and_synthetic_5d_candle_forecast():
    frames = {f"S{k}": _stage2_frame(260, seed=10 + k) for k in range(8)}
    pm = fit_pooled_panel_model(frames)
    assert pm is not None and pm["n_samples"] >= 150
    assert pm.get("brier_score") is None or (0.0 <= pm["brier_score"] <= 0.35)

    fc = walk_forward_and_forecast(frames["S0"], pooled_model=pm)
    assert fc is not None
    assert fc["predicted_low_5d"] <= fc["predicted_price"] <= fc["predicted_high_5d"]
    assert 8.0 <= fc["ml_win_prob_pct"] <= 92.0
    assert "tb_win_acc" in fc["backtest"]


def test_breadth_bear_cash_gate_and_simulation_win_odds():
    assert trade_rules.breadth_pick_cap(22.0, 7) == 0
    assert trade_rules.breadth_pick_cap(29.0, 7, regime="bear") == 0
    assert trade_rules.breadth_pick_cap(36.0, 7, regime="bear") == 2
    assert trade_rules.breadth_pick_cap(37.0, 7, regime="neutral") == 3

    df = _stage2_frame(220)
    ts = trader_score(df)
    m = ts["metrics"]
    pick = {
        "symbol": "TEST",
        "yahoo": "TEST.NS",
        "current_price": m["price"],
        "stop_loss": m["stop_loss"],
        "target": m["target1"],
        "atr": m["atr"],
        "breakeven_at": m["breakeven_at"],
        "breakeven_stop": m["breakeven_stop"],
    }
    sim = sim_mod.simulate_daily_fallback(pick, replays=500, df=df)
    assert sim is not None
    assert "target_hit_probability_pct" in sim and "breakeven_protected_pct" in sim
    assert sim["win_probability_pct"] >= sim["target_hit_probability_pct"]


def test_corporate_actions_split_and_bonus_adjustment():
    from app.datafeed import adjust_corporate_actions

    df = _stage2_frame(120, seed=31)
    # Simulate an unadjusted 1:5 stock split on bar 80 (pre-split prices 5x higher, volume 1/5th)
    raw = df.copy()
    for col in ("Open", "High", "Low", "Close"):
        raw.iloc[:80, raw.columns.get_loc(col)] *= 5.0
    raw.iloc[:80, raw.columns.get_loc("Volume")] /= 5.0

    adj = adjust_corporate_actions(raw)
    seam_ret = abs(float(adj["Close"].iloc[80]) / float(adj["Close"].iloc[79]) - 1.0)
    assert seam_ret < 0.08
    assert np.allclose(adj["Close"].to_numpy(), df["Close"].to_numpy(), rtol=1e-4)


def test_pairwise_correlation_cap_and_liquidity_tiered_costs():
    from app.sectors import apply_correlation_cap
    from app.backtest import tiered_round_trip_cost_pct

    f_base = _stage2_frame(100, seed=77)
    # Clone with 98% return correlation but placed in a DIFFERENT Yahoo sector
    f_clone = f_base.copy()
    f_clone["Close"] = f_base["Close"] * 1.5
    f_indep = _stage2_frame(100, seed=99)

    frames = {"HAL.NS": f_base, "BEL.NS": f_clone, "CIPLA.NS": f_indep}
    ranked = [
        {"symbol": "HAL", "yahoo": "HAL.NS", "sector": "Industrials", "current_price": 4000, "predicted_return_pct": 2.8},
        {"symbol": "BEL", "yahoo": "BEL.NS", "sector": "Technology", "current_price": 300, "predicted_return_pct": 2.5},
        {"symbol": "CIPLA", "yahoo": "CIPLA.NS", "sector": "Healthcare", "current_price": 1500, "predicted_return_pct": 2.2},
    ]
    pool, capped = apply_correlation_cap(ranked, frames_by_key=frames, want=3, max_corr=0.70)
    assert [p["symbol"] for p in pool] == ["HAL", "CIPLA"]
    assert len(capped) == 1 and capped[0]["symbol"] == "BEL" and capped[0]["correlated_with"] == "HAL"

    assert tiered_round_trip_cost_pct(600_000_000) == 0.26
    assert tiered_round_trip_cost_pct(150_000_000) == 0.30
    assert tiered_round_trip_cost_pct(45_000_000) == 0.36
    assert tiered_round_trip_cost_pct(10_000_000) == 0.44
