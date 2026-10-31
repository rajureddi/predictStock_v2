"""Trade-level and portfolio-level statistics shared by the offline backtest
(scripts/backtest_portfolio.py) and the live Track Record (/api/history).

A trade is a dict with at least `ret_pct` (gross % return, entry -> exit).
Optional: `entry`, `stop`, `exit` (to derive the R multiple), `r_multiple`,
`regime` ("bull"/"bear": NIFTY above / below its 200-DMA on entry day),
`mae_pct` / `mfe_pct` (max adverse / favourable excursion while open).
"""
import math
import numpy as np

COST_PER_SIDE_PCT = 0.15  # brokerage + STT + impact, per side (~0.3% round trip)


def _f(x, default=None):
    try:
        v = float(x)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except Exception:
        return default


def r_multiple(entry, stop, exit_price):
    """(exit - entry) / (entry - stop); None when the stop is not usable."""
    entry, stop, exit_price = _f(entry), _f(stop), _f(exit_price)
    if entry is None or stop is None or exit_price is None or entry <= 0 or stop >= entry:
        return None
    return (exit_price - entry) / (entry - stop)


def trade_from_pick(pick, exit_price, regime=None, mae_pct=None, mfe_pct=None):
    """Build a trade record from a published pick and its settled exit price."""
    entry = _f(pick.get("current_price")); exit_price = _f(exit_price)
    if entry is None or exit_price is None or entry <= 0:
        return None
    stop = _f(pick.get("stop_loss"))
    return dict(symbol=pick.get("symbol"), entry=entry, exit=exit_price, stop=stop,
                ret_pct=(exit_price / entry - 1.0) * 100.0,
                r_multiple=r_multiple(entry, stop, exit_price),
                predicted_return_pct=_f(pick.get("predicted_return_pct")),
                regime=regime, mae_pct=mae_pct, mfe_pct=mfe_pct)


def max_consecutive_losses(rets):
    worst = cur = 0
    for r in rets:
        cur = cur + 1 if r <= 0 else 0
        worst = max(worst, cur)
    return worst


def compute_trade_stats(trades, cost_per_side_pct=COST_PER_SIDE_PCT, split_regime=True):
    """Expectancy (R), profit factor, payoff ratio, win rate, max consecutive
    losses, cost-adjusted average return, MAE/MFE, and a bull/bear split.
    Returns a dict with n=0 when there are no usable trades."""
    rows = [t for t in (trades or []) if t and _f(t.get("ret_pct")) is not None]
    rt = 2.0 * cost_per_side_pct
    if not rows:
        return dict(n=0, cost_round_trip_pct=rt)
    gross = np.array([_f(t["ret_pct"]) for t in rows], dtype=float)
    net = gross - rt
    wins, losses = net[net > 0], net[net <= 0]
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(-losses.mean()) if len(losses) else 0.0
    gross_profit = float(wins.sum()); gross_loss = float(-losses.sum())
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    payoff = (avg_win / avg_loss) if avg_loss > 0 else (float("inf") if avg_win > 0 else 0.0)
    win_rate = len(wins) / len(net) * 100.0
    # Expectancy in R: prefer true R multiples (cost converted to R per trade), else %-based proxy
    rs = []
    for t, g in zip(rows, gross):
        r = _f(t.get("r_multiple"))
        if r is None: r = r_multiple(t.get("entry"), t.get("stop"), t.get("exit"))
        if r is not None:
            entry, stop = _f(t.get("entry")), _f(t.get("stop"))
            risk_pct = (entry - stop) / entry * 100.0 if entry and stop and entry > stop else None
            rs.append(r - (rt / risk_pct if risk_pct else 0.0))
    exp_r = float(np.mean(rs)) if rs else None
    exp_pct = (win_rate / 100.0) * avg_win - (1 - win_rate / 100.0) * avg_loss
    mae = [_f(t.get("mae_pct")) for t in rows if _f(t.get("mae_pct")) is not None]
    mfe = [_f(t.get("mfe_pct")) for t in rows if _f(t.get("mfe_pct")) is not None]
    preds = [(_f(t.get("predicted_return_pct")), g) for t, g in zip(rows, gross) if _f(t.get("predicted_return_pct")) is not None]
    dir_hits = [1.0 if (p > 0) == (g > 0) else 0.0 for p, g in preds]
    out = dict(
        n=len(rows), win_rate_pct=round(win_rate, 1),
        avg_return_gross_pct=round(float(gross.mean()), 3), avg_return_net_pct=round(float(net.mean()), 3),
        total_return_net_pct=round(float(net.sum()), 2),
        avg_win_pct=round(avg_win, 3), avg_loss_pct=round(avg_loss, 3),
        payoff_ratio=(round(payoff, 2) if payoff != float("inf") else None),
        profit_factor=(round(pf, 2) if pf != float("inf") else None),
        expectancy_pct=round(exp_pct, 3),
        expectancy_R=(round(exp_r, 3) if exp_r is not None else None), r_trades=len(rs),
        max_consecutive_losses=max_consecutive_losses(net),
        direction_hit_rate_pct=(round(float(np.mean(dir_hits)) * 100, 1) if dir_hits else None),
        avg_mae_pct=(round(float(np.mean(mae)), 2) if mae else None),
        avg_mfe_pct=(round(float(np.mean(mfe)), 2) if mfe else None),
        cost_round_trip_pct=rt,
    )
    if split_regime:
        by = {}
        for reg in ("bull", "bear"):
            sub = [t for t in rows if t.get("regime") == reg]
            if sub:
                by[reg] = compute_trade_stats(sub, cost_per_side_pct, split_regime=False)
        out["by_regime"] = by
    return out


def portfolio_metrics(period_returns_pct, periods_per_year=52):
    """CAGR, max drawdown, Sharpe, Sortino, Calmar from per-period % returns."""
    r = np.array([_f(x, 0.0) for x in (period_returns_pct or [])], dtype=float) / 100.0
    if len(r) == 0:
        return dict(periods=0)
    eq = np.cumprod(1 + r)
    total = float(eq[-1] - 1)
    years = len(r) / periods_per_year
    cagr = (float(eq[-1]) ** (1 / years) - 1) if years > 0 and eq[-1] > 0 else None
    peak = np.maximum.accumulate(eq); dd = eq / peak - 1
    max_dd = float(dd.min())
    sd = float(r.std(ddof=1)) if len(r) > 1 else 0.0
    sharpe = float(r.mean() / sd * math.sqrt(periods_per_year)) if sd > 0 else None
    downside = r[r < 0]
    dsd = float(np.sqrt(np.mean(downside ** 2))) if len(downside) else 0.0
    sortino = float(r.mean() / dsd * math.sqrt(periods_per_year)) if dsd > 0 else None
    calmar = (cagr / abs(max_dd)) if cagr is not None and max_dd < 0 else None
    return dict(periods=len(r), total_return_pct=round(total * 100, 2),
                cagr_pct=(round(cagr * 100, 2) if cagr is not None else None),
                max_drawdown_pct=round(max_dd * 100, 2),
                sharpe=(round(sharpe, 2) if sharpe is not None else None),
                sortino=(round(sortino, 2) if sortino is not None else None),
                calmar=(round(calmar, 2) if calmar is not None else None),
                best_period_pct=round(float(r.max()) * 100, 2), worst_period_pct=round(float(r.min()) * 100, 2),
                positive_periods_pct=round(float((r > 0).mean()) * 100, 1))


def regime_series(nifty_close, window=200):
    """pandas Series of 'bull'/'bear' (close above / below its 200-DMA) per date."""
    import pandas as pd
    s = nifty_close.dropna()
    sma = s.rolling(window).mean()
    out = pd.Series(np.where(s > sma, "bull", "bear"), index=s.index, dtype=object)
    out[sma.isna()] = None
    return out


def regime_on(nifty_close, when, window=200):
    """Regime on (or the last session before) `when`; None when unavailable."""
    try:
        import pandas as pd
        reg = regime_series(nifty_close, window)
        reg = reg[reg.index <= pd.Timestamp(when)]
        if not len(reg): return None
        v = reg.iloc[-1]
        return v if isinstance(v, str) else None
    except Exception:
        return None


def simulate_exit(bars, entry, stop, target, horizon=5):
    """Walk up to `horizon` OHLC bars after entry. Gap at open first, then
    intrabar; a bar touching both levels counts as a stop (conservative).
    Returns dict(exit, reason, bars_held, mae_pct, mfe_pct) or None."""
    if bars is None or len(bars) == 0 or entry <= 0:
        return None
    lo_px, hi_px = entry, entry
    n = 0
    for _, b in bars.head(horizon).iterrows():
        n += 1
        o, h, l, c = float(b["Open"]), float(b["High"]), float(b["Low"]), float(b["Close"])
        lo_px, hi_px = min(lo_px, l), max(hi_px, h)
        if stop and o <= stop: return dict(exit=o, reason="stop_gap", bars_held=n, mae_pct=(lo_px/entry-1)*100, mfe_pct=(hi_px/entry-1)*100)
        if target and o >= target: return dict(exit=o, reason="target_gap", bars_held=n, mae_pct=(lo_px/entry-1)*100, mfe_pct=(hi_px/entry-1)*100)
        hit_stop = bool(stop) and l <= stop; hit_tgt = bool(target) and h >= target
        if hit_stop: return dict(exit=stop, reason="stop", bars_held=n, mae_pct=(lo_px/entry-1)*100, mfe_pct=(hi_px/entry-1)*100)
        if hit_tgt: return dict(exit=target, reason="target", bars_held=n, mae_pct=(lo_px/entry-1)*100, mfe_pct=(hi_px/entry-1)*100)
        last_close = c
    return dict(exit=last_close, reason="time", bars_held=n, mae_pct=(lo_px/entry-1)*100, mfe_pct=(hi_px/entry-1)*100)
