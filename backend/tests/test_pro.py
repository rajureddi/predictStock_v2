import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.engine import detect_patterns, trader_score, walk_forward_and_forecast, build_features
from app.allocate import allocate
from app.universe import parse_nse, parse_bse
from app.pipeline import target_date_for
from datetime import date

def synth(n=400, trend=0.001, seed=7):
    rng = np.random.default_rng(seed); rets = rng.normal(trend, 0.015, n)
    close = 100*np.exp(np.cumsum(rets)); open_ = np.roll(close,1); open_[0]=close[0]
    high = np.maximum(open_, close)*1.005; low = np.minimum(open_, close)*0.995
    vol = rng.integers(100_000, 900_000, n).astype(float)
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({"Open":open_,"High":high,"Low":low,"Close":close,"Volume":vol}, index=idx)

def test_universe_parse_nse():
    txt = "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\nRELIANCE,Reliance Industries,EQ,01-JAN-2000,10,1,INE002A01018,10\n"
    out = parse_nse(txt); assert out[0]["yahoo"] == "RELIANCE.NS" and out[0]["exchange"] == "NSE"

def test_patterns_engulfing():
    idx = pd.bdate_range("2025-01-01", periods=6)
    df = pd.DataFrame({"Open":[100,99,98,97,96,95.0],"High":[101,100,99,98,97,103.0],"Low":[99,98,97,96,95,94.5],
                       "Close":[99.5,98.5,97.5,96.5,95.5,102.0],"Volume":[1e5]*6}, index=idx)
    bull, bear, bp, _ = detect_patterns(df); assert bull >= 1 and "Bullish engulfing" in bp

def test_trader_score_range_and_reasons():
    ts = trader_score(synth()); assert ts is not None and 0 <= ts["score"] <= 100 and len(ts["reasons"]) >= 1
    assert ts["metrics"]["stop_loss"] < ts["metrics"]["price"] < ts["metrics"]["target1"]

def test_backtest_quality_fields():
    fc = walk_forward_and_forecast(synth(n=500))
    assert fc is not None and "best_dir_acc" in fc["backtest"] and "naive_mape" in fc["backtest"]
    assert isinstance(fc["quality_pass"], bool)

def test_walk_forward_uses_latest_row_inference():
    # Verify that the live forecast uses the most recent bar (t_0) features,
    # and that the training matrix only uses historical rows with known targets (X.iloc[:-5]).
    from app.engine import build_features, FEATURES, HORIZON, _fit_predict
    df = synth(n=300)
    d = build_features(df)
    clean = d.dropna(subset=FEATURES)
    
    # Check that clean retains all the way up to the latest timestamp (t_0)
    assert clean.index[-1] == df.index[-1]
    
    # Check target is NaN exactly for the last HORIZON rows
    assert clean["TARGET"].iloc[-HORIZON:].isna().all()
    assert not clean["TARGET"].iloc[:-HORIZON].isna().any()
    
    # Slicing test
    X = clean[FEATURES]
    y = clean["TARGET"]
    X_train = X.iloc[:-HORIZON].values
    y_train = y.iloc[:-HORIZON].values
    X_live = X.iloc[[-1]].values
    
    assert len(X_train) == len(clean) - HORIZON
    assert len(y_train) == len(clean) - HORIZON
    assert X_live.shape == (1, len(FEATURES))
    
    fc = walk_forward_and_forecast(df)
    assert fc is not None
    assert "predicted_return_pct" in fc
    assert "predicted_price" in fc
    # Predicted price must be based on the latest bar's close price
    expected_price = float(df["Close"].iloc[-1]) * (1 + fc["predicted_return_pct"] / 100)
    assert abs(fc["predicted_price"] - expected_price) <= 0.05

def test_allocate_whole_shares_within_budget():
    picks = [dict(symbol="A", current_price=100.0, predicted_price=110.0, trader_score=80, predicted_return_pct=10, backtest={"best_dir_acc":60}),
             dict(symbol="B", current_price=250.0, predicted_price=260.0, trader_score=70, predicted_return_pct=4, backtest={"best_dir_acc":55})]
    a = allocate(picks, 10000); assert a["total_invested"] <= 10000 and a["leftover"] >= 0
    assert all(isinstance(x["shares"], int) for x in a["allocations"])
    assert a["expected_value"] >= 0

def test_allocate_no_budget():
    a = allocate([], None); assert a["allocations"] == []

def test_target_date_plus7():
    assert target_date_for(date(2026,10,26)) == "2026-11-02"  # Monday -> next Monday

def test_overbought_penalty_and_dynamic_rr():
    # Parabolic / extreme RSI frame should be penalised vs normal uptrend, and risk_reward should not be fixed at 1.0
    normal = synth(n=200, trend=0.002, seed=11)
    parabolic = normal.copy()
    # Force a vertical 20-day blow-off (+120%) at the end so RSI > 85 and 60d extension > 100%
    mult = np.linspace(1.0, 2.3, 25)
    for col in ("Open", "High", "Low", "Close"):
        parabolic.iloc[-25:, parabolic.columns.get_loc(col)] *= mult
    ts_norm = trader_score(normal)
    ts_para = trader_score(parabolic)
    assert ts_para["score"] < ts_norm["score"]
    assert any("overbought" in r.lower() or "parabolic" in r.lower() for r in ts_para["reasons"])
    assert ts_norm["metrics"]["risk_reward"] != 1.0

def test_simulation_high_low_reproducible_and_payoff():
    from app.simulation import simulate_daily_fallback
    df = synth(n=260, trend=0.001, seed=21)
    c = float(df["Close"].iloc[-1])
    pick = dict(symbol="TEST", exchange="NSE", current_price=c, stop_loss=round(c*0.96, 2), target=round(c*1.06, 2))
    s1 = simulate_daily_fallback(pick, replays=500, seed=42, df=df)
    s2 = simulate_daily_fallback(pick, replays=500, seed=42, df=df)
    assert s1 is not None and s1 == s2  # strictly reproducible with fixed seed
    assert "avg_R" in s1 and "expected_return_pct" in s1
    assert "High/Low" in s1["method"]

def test_api_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/health").status_code == 200
    r = c.post("/api/screen/budget", json={"budget_inr": 50000}); assert r.json()["budget_inr"] == 50000
    assert c.get("/api/screen/budget").json()["budget_inr"] == 50000
    c.post("/api/screen/budget", json={"budget_inr": None})
    assert c.get("/api/picks/latest").status_code == 200
    assert c.get("/api/history").status_code == 200
