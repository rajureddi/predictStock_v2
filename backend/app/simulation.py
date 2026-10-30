"""Bridge connecting MarketMind Pro stock predictions with 5-Day High/Low Time Machine Monte Carlo & Entry tools."""

import sys
import zlib
import random
from pathlib import Path
from datetime import date
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TRADER_DIR = ROOT / "trader"
if str(TRADER_DIR) not in sys.path:
    sys.path.insert(0, str(TRADER_DIR))

try:
    import timemachine, entry, market
except ImportError:
    timemachine = None
    entry = None
    market = None


def resolve_yahoo_ticker(pick):
    """Resolves correct Yahoo Finance ticker (e.g. 543897.BO for BSE or SSWL.NS for NSE)."""
    if pick.get("yahoo"):
        return pick["yahoo"]
    sym = pick.get("symbol")
    ex = pick.get("exchange", "NSE")
    scrip = pick.get("scrip_code")
    if ex == "BSE" and scrip:
        return f"{scrip}.BO"
    try:
        from app import universe
        u = universe.load_universe()
        for l in u.get("listings", []):
            if l.get("symbol") == sym and (not ex or l.get("exchange") == ex):
                if l.get("yahoo"):
                    return l["yahoo"]
    except Exception:
        pass
    if ex == "BSE":
        return f"{sym}.BO"
    return f"{sym}.NS"


def _verdict_from_payoff(avg_r: float, exp_ret_pct: float, p_target: float, p_stop: float) -> str:
    """Verdict grounded in expected payoff (avg_R and expected return), not just win vs stop count."""
    if avg_r >= 0.35 and exp_ret_pct > 0.5 and p_target >= p_stop:
        return "Strongly toward target"
    if avg_r >= 0.08 and exp_ret_pct > 0:
        return "Leans toward target"
    if avg_r >= -0.05 and exp_ret_pct >= -0.25:
        return "Break-even payoff"
    return "Leans toward stop"


def simulate_daily_fallback(pick, replays=1000, seed=42, df=None):
    """5-day High/Low Monte Carlo simulation using historical OHLC bars and expected payoff."""
    try:
        ticker = resolve_yahoo_ticker(pick)
        if df is None:
            from app import datafeed
            df = datafeed.local_history(ticker)
            if df is None or len(df) < 20:
                df = datafeed.download_one(ticker, period="1y")
        if df is None or len(df) < 20:
            return None

        tail = df.tail(252).copy()
        prev_c = tail["Close"].shift(1)
        valid = tail.dropna(subset=["Open", "High", "Low", "Close"]).iloc[1:]
        prev_c = prev_c.loc[valid.index]
        valid = valid[prev_c > 0]
        prev_c = prev_c[prev_c > 0]
        if len(valid) < 20:
            return None

        ro = (valid["Open"] / prev_c - 1.0).to_numpy(dtype=float)
        rh = (valid["High"] / prev_c - 1.0).to_numpy(dtype=float)
        rl = (valid["Low"] / prev_c - 1.0).to_numpy(dtype=float)
        rc = (valid["Close"] / prev_c - 1.0).to_numpy(dtype=float)

        # Mildly shrink mean daily drift by 40% so past parabolic runs do not guarantee high win odds
        mean_rc = float(np.mean(rc))
        if mean_rc > 0.0015:
            adj = mean_rc * 0.40
            ro = ro - adj
            rh = rh - adj
            rl = rl - adj
            rc = rc - adj

        n_bars = len(rc)
        current_price = float(pick.get("current_price") or 0)
        target = float(pick.get("target") or pick.get("predicted_price") or (current_price * 1.05))
        stop = float(pick.get("stop_loss") or (current_price * 0.95))
        if current_price <= 0 or not (stop < current_price < target):
            return None

        risk_unit = max(current_price - stop, 1e-6)
        target_r = (target - current_price) / risk_unit

        # Deterministic, reproducible RNG per ticker + price configuration
        sym_hash = zlib.crc32(f"{ticker}:{current_price:.2f}:{target:.2f}:{stop:.2f}".encode("utf-8")) & 0xFFFFFFFF
        rng = random.Random((int(seed) ^ sym_hash) & 0xFFFFFFFF)

        hits_target, hits_stop, neither = 0, 0, 0
        final_prices = []
        r_multiples = []

        for _ in range(replays):
            p = current_price
            hit = None
            for _ in range(5):  # 5 trading days horizon
                idx = rng.randrange(n_bars)
                day_open = p * (1.0 + ro[idx])
                day_high = max(day_open, p * (1.0 + rh[idx]))
                day_low = min(day_open, p * (1.0 + rl[idx]))
                day_close = min(day_high, max(day_low, p * (1.0 + rc[idx])))

                # Gap check at open first
                if day_open <= stop:
                    hit = "stop"
                    p = stop
                    break
                if day_open >= target:
                    hit = "target"
                    p = target
                    break

                # Intrabar High/Low check (conservative on ambiguous both-hit days)
                hit_low = day_low <= stop
                hit_high = day_high >= target
                if hit_low and hit_high:
                    # If bearish bar or open is closer to stop, count as stop-first
                    if rc[idx] <= ro[idx] or (day_open - stop) <= (target - day_open):
                        hit = "stop"
                        p = stop
                    else:
                        hit = "target"
                        p = target
                    break
                elif hit_low:
                    hit = "stop"
                    p = stop
                    break
                elif hit_high:
                    hit = "target"
                    p = target
                    break

                p = day_close

            if hit == "target":
                hits_target += 1
                r_multiples.append(target_r)
            elif hit == "stop":
                hits_stop += 1
                r_multiples.append(-1.0)
            else:
                neither += 1
                r_multiples.append((p - current_price) / risk_unit)
            final_prices.append(p)

        final_prices.sort()
        p_target = round(hits_target / replays * 100, 1)
        p_stop = round(hits_stop / replays * 100, 1)
        p_neither = round(neither / replays * 100, 1)
        median_c = round(final_prices[len(final_prices) // 2], 2)
        p5 = round(final_prices[int(len(final_prices) * 0.05)], 2)
        p95 = round(final_prices[int(len(final_prices) * 0.95)], 2)
        avg_r = round(float(np.mean(r_multiples)), 3)
        exp_ret_pct = round(float(np.mean([(fp - current_price) / current_price * 100.0 for fp in final_prices])), 2)
        verdict = _verdict_from_payoff(avg_r, exp_ret_pct, p_target, p_stop)

        return {
            "win_probability_pct": p_target,
            "loss_probability_pct": p_stop,
            "neither_probability_pct": p_neither,
            "median_close": median_c,
            "expected_p5": p5,
            "expected_p95": p95,
            "avg_R": avg_r,
            "expected_return_pct": exp_ret_pct,
            "verdict": verdict,
            "replays": replays,
            "seed": seed,
            "sessions": int(n_bars),
            "method": "5-Day High/Low Time Machine (OHLC bootstrap)"
        }
    except Exception:
        return None


def simulate_pick(pick, replays=1000, log=None, seed=42, df=None):
    """Runs a reproducible 5-day High/Low Monte Carlo simulation on a pick's target & stop-loss."""
    current_price = float(pick.get("current_price") or 0)
    target = float(pick.get("target") or pick.get("predicted_price") or (current_price * 1.05))
    stop = float(pick.get("stop_loss") or (current_price * 0.95))

    if current_price <= 0 or not (stop < current_price < target):
        return None

    res = simulate_daily_fallback(pick, replays=replays, seed=seed, df=df)
    if res is not None:
        return res

    # Fallback to 5-minute intraday Time Machine only if daily history is unavailable
    ticker = resolve_yahoo_ticker(pick)
    if timemachine and market:
        plan = {
            "created_by": "MarketMindPro",
            "symbol": ticker,
            "side": "buy",
            "date": str(date.today()),
            "setup": "orb",
            "entry": round(current_price, 2),
            "stop": round(stop, 2),
            "target": round(target, 2),
            "entry_bar": 3,
            "entry_time": "9:35 AM"
        }
        try:
            norm_plan = timemachine.normalize_plan(plan)
            chart_text = timemachine.fetch_chart(ticker)
            tm = timemachine.time_machine(chart_text, norm_plan, now_utc=timemachine.parse_now(None), replays=replays, seed=seed)
            mc = tm.get("mc", {})
            p_target = round(mc.get("p_target", 0) * 100, 1)
            p_stop = round(mc.get("p_stop", 0) * 100, 1)
            avg_r = round(float(mc.get("avg_R") or 0.0), 3)
            med = mc.get("median_close") or current_price
            exp_ret_pct = round(((float(med) - current_price) / current_price) * 100.0, 2)
            return {
                "win_probability_pct": p_target,
                "loss_probability_pct": p_stop,
                "neither_probability_pct": round(mc.get("p_neither", 0) * 100, 1),
                "median_close": mc.get("median_close"),
                "expected_p5": mc.get("p5_close"),
                "expected_p95": mc.get("p95_close"),
                "avg_R": avg_r,
                "expected_return_pct": exp_ret_pct,
                "verdict": _verdict_from_payoff(avg_r, exp_ret_pct, p_target, p_stop),
                "replays": replays,
                "seed": seed,
                "sessions": mc.get("pool_sessions", 0),
                "method": "5-minute intraday Time Machine (60-day bars)"
            }
        except Exception as e:
            if log:
                log(f"[simulation] 5m intraday failed for {ticker} ({e})")
    return None


def check_orb_status(pick):
    """Checks if the stock triggered a 9:15-9:30 AM Opening Range Breakout today."""
    if not entry or not market:
        return None
    ticker = resolve_yahoo_ticker(pick)
    try:
        chart = entry.get_chart(ticker, "5m")
        ev = entry.evaluate(chart, entry.utc_now(), setup="orb", or_minutes=15)
        trig = ev.get("trigger") or {}
        rng = ev.get("opening_range") or {}
        return {
            "status": ev.get("status"),
            "trigger_price": trig.get("price"),
            "trigger_time": trig.get("time"),
            "range_high": rng.get("high"),
            "range_low": rng.get("low")
        }
    except Exception:
        return None
