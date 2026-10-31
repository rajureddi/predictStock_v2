"""Market regime gate + volatility sizing.

Long-only 5-day momentum fails in downtrends: the 104-week backtest lost most
of its drawdown in weeks NIFTY traded below its 200-DMA. This module turns the
index trend (NIFTY vs 50/200-DMA) and India VIX (level + 5-day change) into
portfolio-level knobs the pipeline applies to every pick:

    max_picks   how many picks to publish          (bull 7 / neutral 5 / bear 3)
    cash_pct    share of budget held back in cash  (0 / 0.20 / 0.50)
    size_mult   position size multiplier from VIX  (1.0 calm .. 0.5 panic)
    stop_widen  ATR stop multiplier from VIX       (1.0 .. 1.25)

A data failure must never break the pipeline: `get_market_regime()` falls back
to an "unknown" regime that leaves existing behaviour untouched.
"""
import math

REGIME_RULES = {
    "bull":    dict(max_picks=7, cash_pct=0.0),
    "neutral": dict(max_picks=5, cash_pct=0.20),
    "bear":    dict(max_picks=3, cash_pct=0.50),
    "unknown": dict(max_picks=7, cash_pct=0.0),
}


def _f(x, default=None):
    try:
        v = float(x)
        return v if not (math.isnan(v) or math.isinf(v)) else default
    except Exception:
        return default


def classify_trend(close, sma50, sma200):
    """bull: above both averages with 50 > 200. bear: below the 200-DMA, or
    below the 50-DMA while the 50 is itself under the 200 (dead cross).
    Everything else is neutral."""
    if close is None or sma200 is None:
        return "unknown"
    if sma50 is None:
        return "bull" if close > sma200 else "bear"
    if close > sma50 and close > sma200 and sma50 >= sma200:
        return "bull"
    if close < sma200 or (close < sma50 and sma50 < sma200):
        return "bear"
    return "neutral"


def vix_adjustments(vix, vix_chg5_pct):
    """(size_mult, stop_widen, note). VIX > 18 and rising = smaller size and
    wider stops; a VIX spike (> +20% in 5 days) is treated like a higher level."""
    if vix is None:
        return 1.0, 1.0, "VIX unavailable — no volatility adjustment"
    chg = vix_chg5_pct or 0.0
    eff = vix * (1.10 if chg > 20 else 1.0)  # a spike counts as one band higher
    if eff < 15:      size, widen, band = 1.00, 1.00, "calm"
    elif eff < 18:    size, widen, band = 0.90, 1.05, "normal"
    elif eff < 22:    size, widen, band = 0.75, 1.15, "elevated"
    else:             size, widen, band = 0.50, 1.25, "high"
    if chg > 10 and eff >= 15:
        size = round(size * 0.9, 3)
    note = f"India VIX {vix:.1f} ({'+' if chg >= 0 else ''}{chg:.0f}% in 5 days) — {band} volatility"
    return size, widen, note


def compute_regime(nifty_close=None, vix_close=None):
    """Pure function: pandas Series of NIFTY closes (>= 200 rows for a full
    read) and India VIX closes (>= 6 rows). Returns the regime dict."""
    close = sma50 = sma200 = None
    if nifty_close is not None and len(nifty_close):
        s = nifty_close.dropna()
        close = _f(s.iloc[-1])
        if len(s) >= 50:  sma50 = _f(s.tail(50).mean())
        if len(s) >= 200: sma200 = _f(s.tail(200).mean())
    trend = classify_trend(close, sma50, sma200)
    vix = vix_chg = None
    if vix_close is not None and len(vix_close):
        v = vix_close.dropna()
        vix = _f(v.iloc[-1])
        if len(v) >= 6 and _f(v.iloc[-6], 0) > 0:
            vix_chg = round((float(v.iloc[-1]) / float(v.iloc[-6]) - 1.0) * 100.0, 1)
    size_mult, stop_widen, vix_note = vix_adjustments(vix, vix_chg)
    rules = REGIME_RULES[trend]
    pct200 = round((close / sma200 - 1.0) * 100.0, 2) if close and sma200 else None
    pct50 = round((close / sma50 - 1.0) * 100.0, 2) if close and sma50 else None
    if trend == "bull":
        headline = "Bull regime — NIFTY above its 50- and 200-DMA. Full pick count."
    elif trend == "bear":
        headline = "Bear regime — NIFTY below its 200-DMA. Picks cut to 3, half the budget held in cash."
    elif trend == "neutral":
        headline = "Neutral regime — NIFTY between its averages. Picks cut to 5, 20% cash reserve."
    else:
        headline = "Market regime unavailable — no regime adjustment applied."
    return dict(regime=trend, headline=headline,
                nifty_close=round(close, 2) if close else None,
                nifty_sma50=round(sma50, 2) if sma50 else None,
                nifty_sma200=round(sma200, 2) if sma200 else None,
                nifty_vs_50dma_pct=pct50, nifty_vs_200dma_pct=pct200,
                vix=round(vix, 2) if vix is not None else None, vix_change_5d_pct=vix_chg, vix_note=vix_note,
                max_picks=rules["max_picks"], cash_pct=rules["cash_pct"],
                size_mult=size_mult, stop_widen=stop_widen)


def get_market_regime(log=print):
    """Fetches ^NSEI (2y) and ^INDIAVIX (3mo) and classifies. Never raises."""
    try:
        from app import datafeed
        nifty = datafeed.download_batch(["^NSEI"], period="2y").get("^NSEI")
        vix = None
        try:
            vix = datafeed.download_batch(["^INDIAVIX"], period="3mo").get("^INDIAVIX")
        except Exception as e:
            log(f"[regime] VIX fetch failed: {e}")
        reg = compute_regime(nifty["Close"] if nifty is not None else None,
                             vix["Close"] if vix is not None else None)
        log(f"[regime] {reg['regime'].upper()}: NIFTY {reg['nifty_close']} vs 200-DMA {reg['nifty_sma200']} "
            f"({reg['nifty_vs_200dma_pct']}%) · {reg['vix_note']} -> max_picks={reg['max_picks']} "
            f"cash={reg['cash_pct']:.0%} size×{reg['size_mult']} stop×{reg['stop_widen']}")
        return reg
    except Exception as e:
        log(f"[regime] unavailable: {e}")
        return compute_regime(None, None)


def apply_stop_widen(pick, stop_widen):
    """Widen the pick's stop by the VIX multiplier (distance from entry scales,
    stop stays below price) and recompute risk_reward. Mutates and returns."""
    try:
        if not stop_widen or abs(stop_widen - 1.0) < 1e-9:
            return pick
        price = float(pick.get("current_price") or 0)
        stop = float(pick.get("stop_loss") or 0)
        target = float(pick.get("target") or 0)
        if price <= 0 or stop <= 0 or stop >= price:
            return pick
        pick["stop_loss_base"] = round(stop, 2)
        new_stop = round(max(0.05, price - (price - stop) * stop_widen), 2)
        pick["stop_loss"] = new_stop
        if target > price:
            pick["risk_reward"] = round((target - price) / max(price - new_stop, 1e-9), 2)
    except Exception:
        pass
    return pick
