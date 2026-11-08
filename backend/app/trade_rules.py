"""Dalal Street Institutional 5-Day Trade Rules shared by the live screen and walk-forward backtest.

- Multi-horizon Relative Strength vs NIFTY (5 / 21 / 63 sessions)
- Market Breadth & Bear/Waterfall Regime cash-preservation gate
- Strict >60%-edge tradeability gate: zero fallbacks (stay in cash when edge is absent)
- 'Mooli Salamat' (Protect Principal) 5-day trade plan & multi-factor ranking
"""
from datetime import date, timedelta
from typing import Any, Dict, Iterable, Optional

import pandas as pd

MIN_PRED_RET = 0.72
MAX_RSI = 73.0
MIN_RR = 0.78
MIN_AVG_R = 0.01
MIN_SIM_WIN_PROB = 54.0
MIN_ML_WIN_PROB = 53.5
MAX_STOP_PROB = 38.0
MIN_RS21 = -0.5

BREADTH_NO_TRADE = 24.0
BREADTH_WEAK = 42.0


def _ret(close: pd.Series, n: int) -> Optional[float]:
    close = close.dropna()
    if len(close) <= n:
        return None
    return float(close.iloc[-1] / close.iloc[-1 - n] - 1.0) * 100.0


def relative_strength(close: pd.Series, nifty_close: Optional[pd.Series]) -> Dict[str, Optional[float]]:
    """Stock return minus NIFTY return, in percentage points (5d, 21d, 63d).
    `close` and `nifty_close` must already be sliced to the evaluation date."""
    out = {"rs5_pct": None, "rs21_pct": None, "rs63_pct": None}
    if nifty_close is None or close is None or len(close) == 0:
        return out
    nc = nifty_close[nifty_close.index <= close.index[-1]]
    for n, key in ((5, "rs5_pct"), (21, "rs21_pct"), (63, "rs63_pct")):
        s, m = _ret(close, n), _ret(nc, n)
        if s is not None and m is not None:
            out[key] = round(s - m, 2)
    return out


def market_breadth(closes: Iterable[pd.Series]) -> Optional[float]:
    """% of the given (already date-sliced) close series trading above their 50-DMA."""
    above = total = 0
    for c in closes:
        c = c.dropna()
        if len(c) < 50:
            continue
        total += 1
        if float(c.iloc[-1]) > float(c.tail(50).mean()):
            above += 1
    return round(above / total * 100.0, 1) if total >= 20 else None


def breadth_pick_cap(
    breadth_pct: Optional[float],
    want: int,
    regime: Optional[str] = None,
    nifty_ret5_pct: Optional[float] = None,
) -> int:
    """Dalal Street capital-preservation discipline ('Bazaar thanda -> Cash rakho')."""
    if breadth_pct is not None:
        if breadth_pct < BREADTH_NO_TRADE:
            return 0
        if regime == "bear" and breadth_pct < 31.0:
            return 0
        if nifty_ret5_pct is not None and nifty_ret5_pct < -3.0 and breadth_pct < 42.0:
            return 0
        if regime == "bear" and breadth_pct < BREADTH_WEAK:
            return min(want, 2)
        if breadth_pct < BREADTH_WEAK:
            return min(want, 3)
    elif regime == "bear" and nifty_ret5_pct is not None and nifty_ret5_pct < -2.5:
        return 0
    return want


def gate_failures(c: Dict[str, Any]) -> list:
    """Reasons a candidate fails the institutional 5-day swing gate. Empty list = tradeable."""
    why = []
    if not c.get("quality_pass"):
        why.append("model walk-forward accuracy / win probability below institutional threshold")
    if (c.get("predicted_return_pct") or 0) < MIN_PRED_RET:
        why.append(f"predicted 5-day move < {MIN_PRED_RET}%")
    if (c.get("rsi") or 50) > MAX_RSI:
        why.append(f"RSI > {MAX_RSI:.0f} (overbought chase risk)")
    if (c.get("risk_reward") or 0) < MIN_RR:
        why.append(f"reward:risk < {MIN_RR}")

    # Short-horizon 3-5d anti-chase guard
    ret3 = c.get("ret3")
    ret5 = c.get("ret5")
    if (ret3 is not None and ret3 > 0.075) or (ret5 is not None and ret5 > 0.105):
        why.append("extended 3-5d spike (high 1-week profit-booking risk)")

    # Cash-market operator churn guard
    deliv = c.get("delivery_pct")
    vr = c.get("volume_ratio") or 1.0
    if deliv is not None and deliv < 25.0 and vr >= 1.7:
        why.append("intraday operator churn (<25% delivery on volume spike)")

    # Relative strength & sector leadership
    rs21 = c.get("rs21_pct")
    rs63 = c.get("rs63_pct")
    if rs21 is not None and rs21 < MIN_RS21:
        why.append("underperforming NIFTY over 21 sessions")
    if rs21 is not None and rs63 is not None and rs21 <= 0.0 and rs63 <= 0.0:
        why.append("lagging NIFTY across both 1M and 3M horizons")

    sec_rs = c.get("sector_rs_1m_pct")
    if sec_rs is not None and sec_rs < -3.0:
        why.append("sector in sharp 1-month institutional distribution")

    ml_wp = c.get("ml_win_prob_pct")
    if ml_wp is not None and ml_wp < MIN_ML_WIN_PROB:
        why.append(f"calibrated ML win probability < {MIN_ML_WIN_PROB:.0f}%")

    fund = c.get("fundamentals")
    if isinstance(fund, dict) and fund.get("score") is not None and fund["score"] < 28.0:
        why.append("distressed fundamentals (score < 28)")

    sim = c.get("simulation") or {}
    if sim:
        if (sim.get("avg_R") or 0) < MIN_AVG_R:
            why.append("simulated net expected payoff below threshold")
        if (sim.get("win_probability_pct") or 0) < MIN_SIM_WIN_PROB:
            why.append(f"simulated 5D net win odds < {MIN_SIM_WIN_PROB:.0f}%")
        if (sim.get("loss_probability_pct") or 0) > MAX_STOP_PROB:
            why.append(f"stop-hit odds > {MAX_STOP_PROB:.0f}%")
    return why


def trade_plan(c: Dict[str, Any], run_date: Optional[date] = None) -> Dict[str, Any]:
    price = float(c.get("current_price") or 0)
    stop = float(c.get("stop_loss") or 0)
    t1 = c.get("target")
    atr = float(c.get("atr") or (price * 0.02))
    be_at = round(float(c.get("breakeven_at") or (price + 0.75 * atr)), 2) if price > 0 else None
    be_stop = round(float(c.get("breakeven_stop") or (price * 1.0042)), 2) if price > 0 else None
    risk = round(price - stop, 2) if 0 < stop < price else None
    rd = run_date or date.today()
    entry_cap = round(min(price * 1.01, price + 0.35 * atr), 2) if price > 0 else 0.0
    return {
        "entry_max": entry_cap,
        "entry_note": f"Buy near open only up to ₹{entry_cap:.2f}; skip if it gaps higher (never chase gap-ups).",
        "stop_loss": round(stop, 2) if stop else None,
        "breakeven_trigger": be_at,
        "breakeven_stop": be_stop,
        "target1": t1,
        "target2": c.get("target2"),
        "risk_per_share": risk,
        "risk_pct": round(risk / price * 100, 2) if risk and price else None,
        "time_exit_date": (rd + timedelta(days=7)).isoformat(),
        "rules": [
            "Place the initial structural stop-loss immediately after entry.",
            f"Mooli Salamat (Protect Capital): once price touches ₹{be_at:.2f}, trail stop to ₹{be_stop:.2f} (cost-covered breakeven)." if be_at and be_stop else "Move stop to cost-covered breakeven once +0.75 ATR in profit.",
            "Book partial/full profit at Target 1; trail any runner toward Target 2.",
            "Exit at the Day-5 session close on the time-exit date if neither stop nor target triggers.",
        ],
    }


def rank_key(e: Dict[str, Any]) -> float:
    """Sort key (ascending). Prioritizes calibrated 5D win probability, net Monte Carlo
    payoff, Dalal Street setup quality, relative/sector strength, and fundamentals."""
    fs = (e.get("fundamentals") or {}).get("score")
    fs = 50.0 if fs is None else float(fs)
    sim = e.get("simulation") or {}
    avg_r = float(sim.get("avg_R", 0.0) or 0.0)
    win_p = float(sim.get("win_probability_pct", 55.0) or 55.0)
    stop_p = float(sim.get("loss_probability_pct", 30.0) or 30.0)
    ml_wp = float(e.get("ml_win_prob_pct") or 55.0)
    asym = float(e.get("candle_asymmetry") or 1.0)
    rr = float(e.get("risk_reward") or 1.0)
    rs = float(e.get("rs21_pct") or 0.0)
    sec_rs = float(e.get("sector_rs_1m_pct") or 0.0)
    sec_acc = float(e.get("sector_rotation_accel_pct") or 0.0)
    rsi = float(e.get("rsi") or 55.0)
    ob_pen = (rsi - 70.0) * 1.8 if rsi > 70.0 else 0.0

    setup_bonus = 4.5 if e.get("setup_type") in ("Pullback Reversal", "VCP Coil Expansion") else 0.0
    px = float(e.get("current_price") or 0.0)
    gain_rs = max(0.0, float(e.get("predicted_price") or 0.0) - px)
    # Require > ₹100 5-day profit without chasing ultra-expensive ₹8,000–₹50,000 stocks
    rupee_swing_bonus = 4.5 if gain_rs >= 100.0 else (-4.0 if gain_rs < 60.0 else 1.5)
    heavy_price_pen = 6.0 if px > 4500.0 else 0.0

    score = (
        float(e.get("trader_score", 50)) * 0.24
        + (ml_wp - 50.0) * 0.65
        + (win_p - 50.0) * 0.40
        + avg_r * 35.0
        - stop_p * 0.18
        + min(max(asym - 1.0, -0.4), 0.8) * 6.0
        + min(max(rs, -10.0), 15.0) * 0.65
        + min(max(sec_rs, -8.0), 8.0) * 0.90
        + min(max(sec_acc, -4.0), 4.0) * 0.65
        + (fs - 50.0) * 0.28
        + min(rr - 0.7, 1.5) * 3.0
        + min(float(e.get("predicted_return_pct") or 0.0), 6.0) * 0.85
        + float((e.get("backtest") or {}).get("best_dir_acc", 50.0)) * 0.12
        + setup_bonus
        + rupee_swing_bonus
        - heavy_price_pen
        - ob_pen
    )
    return -score
