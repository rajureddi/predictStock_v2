"""Regime gate, VIX sizing, surveillance/earnings veto, sector cap, ATR risk
sizing and trade statistics (items 1-4 of the trader-metrics plan)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.regime import compute_regime, apply_stop_widen, vix_adjustments
from app.surveillance import extract_symbols, surveillance_flags, apply_surveillance_veto, earnings_in_window, apply_earnings_filter
from app.sectors import apply_sector_cap
from app.allocate import allocate
from app import backtest as bt


def _series(start, end, n=260):
    return pd.Series(np.linspace(start, end, n), index=pd.date_range("2024-01-01", periods=n, freq="B"))


def test_regime_bull_neutral_bear_and_unknown():
    bull = compute_regime(_series(20000, 25000), None)
    assert bull["regime"] == "bull" and bull["max_picks"] == 7 and bull["cash_pct"] == 0
    bear = compute_regime(_series(25000, 20000), None)
    assert bear["regime"] == "bear" and bear["max_picks"] == 3 and bear["cash_pct"] == 0.5
    unknown = compute_regime(None, None)
    assert unknown["regime"] == "unknown" and unknown["max_picks"] == 7 and unknown["size_mult"] == 1.0
    # short series (< 200 rows) cannot classify -> unknown, never raises
    assert compute_regime(_series(100, 110, n=30), None)["regime"] == "unknown"


def test_vix_sizing_and_stop_widen():
    assert vix_adjustments(12, 0)[:2] == (1.0, 1.0)
    size, widen, _ = vix_adjustments(20, 25)       # elevated AND spiking
    assert size < 0.75 and widen >= 1.15
    assert vix_adjustments(25, 0)[0] == 0.5
    p = dict(current_price=100.0, stop_loss=96.0, target=110.0, risk_reward=2.5)
    apply_stop_widen(p, 1.25)
    assert p["stop_loss"] == 95.0 and p["stop_loss_base"] == 96.0 and p["risk_reward"] == 2.0
    q = dict(current_price=100.0, stop_loss=96.0, target=110.0)
    apply_stop_widen(q, 1.0); assert q["stop_loss"] == 96.0 and "stop_loss_base" not in q


def test_surveillance_flags_and_veto():
    payload = {"longterm": {"data": [{"symbol": "AAA"}]}, "shortterm": {"data": [{"symbol": "BBB", "x": 1}]}}
    assert extract_symbols(payload) == ["AAA", "BBB"]
    lists = dict(asm={"AAA"}, gsm={"CCC"})
    assert surveillance_flags("AAA", "NSE", "EQ", lists) == ["ASM"]
    assert surveillance_flags("CCC", "NSE", "BE", lists) == ["GSM", "T2T"]
    assert surveillance_flags("AAA", "BSE", "EQ", lists) == []       # BSE names are not on NSE lists
    assert surveillance_flags("DDD", "NSE", "BZ", None) == ["T2T"]   # T2T works with no NSE data at all
    cands = [dict(symbol=s, exchange="NSE", name=s, current_price=10, trader_score=60) for s in ("AAA", "DDD", "EEE")]
    clean, vetoed = apply_surveillance_veto(cands, series_map={("DDD", "NSE"): "BE"}, lists=lists, log=lambda *_: None)
    assert [c["symbol"] for c in clean] == ["EEE"]
    assert {v["symbol"]: v["flags"] for v in vetoed} == {"AAA": ["ASM"], "DDD": ["T2T"]}


def test_earnings_window_filter():
    assert earnings_in_window(["2026-10-20", "2026-11-03"], "2026-10-31", "2026-11-07") == "2026-11-03"
    assert earnings_in_window(["2026-11-20"], "2026-10-31", "2026-11-07") is None
    ranked = [dict(symbol=str(i), yahoo=str(i)) for i in range(6)]
    dates = {"1": ["2026-11-02"], "4": ["2026-12-01"]}
    pool, skipped = apply_earnings_filter(ranked, "2026-10-31", "2026-11-07", keep=3, dates_by_yahoo=dates, log=lambda *_: None)
    assert [p["symbol"] for p in skipped] == ["1"] and len(pool) == 5
    assert ranked[1]["earnings_in_window"] is True and ranked[4]["earnings_in_window"] is False and ranked[4]["earnings_date"] == "2026-12-01"
    # not enough clean picks -> nothing skipped, still flagged
    pool2, skipped2 = apply_earnings_filter(ranked[:3], "2026-10-31", "2026-11-07", keep=3, dates_by_yahoo=dates, log=lambda *_: None)
    assert skipped2 == [] and len(pool2) == 3 and pool2[1]["earnings_in_window"]


def test_sector_cap_two_per_sector_fills_only_when_short():
    ranked = [dict(symbol="P1", sector="Pharma"), dict(symbol="P2", sector="Pharma"), dict(symbol="P3", sector="Pharma"),
              dict(symbol="I1", sector="IT"), dict(symbol="N1", sector=None), dict(symbol="P4", sector="Pharma")]
    pool, capped = apply_sector_cap(ranked, want=4)
    assert [p["symbol"] for p in pool] == ["P1", "P2", "I1", "N1"]
    assert [c["symbol"] for c in capped] == ["P3", "P4"]
    pool, capped = apply_sector_cap(ranked, want=5)   # short pool: the best capped name fills the slot, in rank order
    assert [p["symbol"] for p in pool] == ["P1", "P2", "P3", "I1", "N1"] and [c["symbol"] for c in capped] == ["P4"]
    assert pool[2].get("sector_cap_filled") is True


def test_allocate_risk_sizing_caps_and_keys():
    picks = [dict(symbol="TIGHT", current_price=100.0, stop_loss=98.0, predicted_price=105.0),
             dict(symbol="WIDE", current_price=100.0, stop_loss=90.0, predicted_price=105.0),
             dict(symbol="NOSTOP", current_price=50.0, predicted_price=52.0)]
    a = allocate(picks, 100_000, risk_pct=1.0, size_mult=1.0, cash_pct=0.0)
    for k in ("budget_inr", "allocations", "total_invested", "leftover", "expected_value", "expected_profit", "risk_inr", "risk_pct", "cash_reserve"):
        assert k in a
    by = {x["symbol"]: x for x in a["allocations"]}
    assert a["risk_inr"] == 1000.0
    assert by["WIDE"]["shares"] == 100 and by["WIDE"]["risk_inr"] == 1000.0           # ₹1000 / ₹10 per share
    assert by["TIGHT"]["shares"] == 300 and by["TIGHT"]["invested"] == 30_000.0       # 500 by risk, capped at 30%
    assert by["NOSTOP"]["shares"] == 500                                                # 4% fallback stop
    assert all(x["risk_inr"] <= a["risk_inr"] + 1e-6 for x in a["allocations"])
    assert a["total_invested"] <= 100_000 and a["leftover"] >= 0
    # regime: half the budget in cash and half size -> everything scales down, cash reserve reported
    b = allocate(picks, 100_000, size_mult=0.5, cash_pct=0.5)
    assert b["cash_reserve"] == 50_000.0 and b["total_invested"] <= 50_000 and b["risk_inr"] == 500.0
    assert allocate(picks, None)["allocations"] == [] and allocate([], 1000)["cash_reserve"] == 0


def test_trade_stats_and_portfolio_metrics():
    trades = [dict(ret_pct=4.0, entry=100, stop=96, exit=104, regime="bull", predicted_return_pct=1.0),
              dict(ret_pct=-4.0, entry=100, stop=96, exit=96, regime="bear", predicted_return_pct=1.0),
              dict(ret_pct=2.0, entry=100, stop=96, exit=102, regime="bull", predicted_return_pct=1.0),
              dict(ret_pct=-1.0, entry=100, stop=96, exit=99, regime="bear", predicted_return_pct=1.0)]
    s = bt.compute_trade_stats(trades, cost_per_side_pct=0.15)
    assert s["n"] == 4 and s["win_rate_pct"] == 50.0 and s["cost_round_trip_pct"] == 0.3
    assert s["avg_return_net_pct"] == round(0.25 - 0.3, 3)
    # gross R = (1, -1, .5, -.25) avg .0625 ; cost .3% on 4% risk = .075R per trade
    assert abs(s["expectancy_R"] - (0.0625 - 0.075)) < 1e-6
    assert s["payoff_ratio"] > 1 and s["profit_factor"] > 1 and s["max_consecutive_losses"] == 1
    assert s["direction_hit_rate_pct"] == 50.0
    assert s["by_regime"]["bull"]["win_rate_pct"] == 100.0 and s["by_regime"]["bear"]["win_rate_pct"] == 0.0
    assert bt.compute_trade_stats([])["n"] == 0
    pm = bt.portfolio_metrics([2.0, -1.0, 3.0, -2.0])
    assert pm["periods"] == 4 and pm["max_drawdown_pct"] < 0 and pm["sharpe"] is not None and pm["sortino"] is not None
    assert bt.max_consecutive_losses([-1, -1, 1, -1, -1, -1, 1]) == 3


def test_regime_on_and_simulate_exit():
    close = _series(20000, 25000)
    assert bt.regime_on(close, close.index[-1]) == "bull"
    assert bt.regime_on(_series(25000, 20000), "2024-12-20") == "bear"
    assert bt.regime_on(close, "2024-02-01") is None   # inside the 200-day warm-up
    idx = pd.date_range("2025-01-01", periods=5, freq="B")
    bars = pd.DataFrame(dict(Open=[101, 102, 103, 104, 105], High=[103, 104, 111, 106, 107],
                             Low=[99, 100, 101, 102, 103], Close=[102, 103, 104, 105, 106]), index=idx)
    ex = bt.simulate_exit(bars, entry=100, stop=95, target=110)
    assert ex["reason"] == "target" and ex["exit"] == 110 and ex["bars_held"] == 3 and ex["mae_pct"] == -1.0
    ex2 = bt.simulate_exit(bars, entry=100, stop=99.5, target=120)
    assert ex2["reason"] == "stop" and ex2["bars_held"] == 1
    ex3 = bt.simulate_exit(bars, entry=100, stop=90, target=120)
    assert ex3["reason"] == "time" and ex3["exit"] == 106


def test_api_backtest_and_history_track_record():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/backtest"); assert r.status_code == 200 and "available" in r.json()
    h = c.get("/api/history").json()
    assert "track_record" in h and "n" in h["track_record"]
