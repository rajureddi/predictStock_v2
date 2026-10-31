"""Weekly portfolio backtest with transaction costs and a regime split.

Replays the pipeline's selection logic (trader_score -> walk-forward ML ->
rank_key, stop/target exits over 5 bars) week by week over the most liquid
NSE stocks, and compares:

    baseline      top-N every week, full size
    regime_gated  pick count / cash / size from app.regime (NIFTY 50/200-DMA + VIX)

Costs: 0.15% per side (~0.3% round trip) on every trade. Output:
data/reports/backtest_summary.json (served by GET /api/backtest).

    python backend/scripts/backtest_portfolio.py --weeks 104 --top 6 --stocks 45
    python backend/scripts/backtest_portfolio.py --fast      # trader_score only, no ML

The ML stage dominates runtime (~1-2 s per stock-week); `--prefilter` limits it
to the top-K trader scores each week.
"""
import argparse, json, sys, time
from datetime import date
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import datafeed, universe as univ_mod, backtest as bt
from app.engine import trader_score, walk_forward_and_forecast, HORIZON
from app.pipeline import rank_key
from app.regime import compute_regime, apply_stop_widen

OUT = ROOT / "data" / "reports" / "backtest_summary.json"


def pick_universe(n_stocks, min_rows=200, log=print):
    """Most liquid NSE 'EQ' listings by average daily traded value (local Bhavcopy panel)."""
    uni = univ_mod.load_universe()
    rows = []
    for l in uni["listings"]:
        if l["exchange"] != "NSE" or (l.get("series") or "EQ") != "EQ": continue
        df = datafeed.local_history(l["yahoo"])
        if df is None or len(df) < min_rows: continue
        tv = float((df["Close"] * df["Volume"]).tail(60).mean())
        rows.append((tv, l["yahoo"]))
    rows.sort(reverse=True)
    picked = [y for _, y in rows[:n_stocks]]
    log(f"[universe] {len(rows)} NSE EQ with >= {min_rows} local rows; using top {len(picked)} by traded value")
    return picked


def load_history(tickers, log=print):
    """Long Yahoo history (5y) merged with the local exchange panel."""
    out = {}
    for i in range(0, len(tickers), 40):
        chunk = tickers[i:i + 40]
        yh = datafeed._yahoo_batch(chunk, period="5y")
        for t in chunk:
            merged = datafeed._merge(datafeed.local_history(t), yh.get(t))
            if merged is not None and len(merged) >= 300: out[t] = merged
        log(f"[history] {len(out)}/{len(tickers)} loaded")
    return out


def evaluate_week(stocks, nifty_close, t, prefilter, fast, log):
    """Candidates as of close `t` (no look-ahead: frames are sliced to <= t)."""
    scored = []
    nc = nifty_close[nifty_close.index <= t]
    for yh, df in stocks.items():
        d = df[df.index <= t]
        if len(d) < 150 or d.index[-1] != t: continue
        try: ts = trader_score(d, nc)
        except Exception: continue
        if ts is None: continue
        scored.append((ts, yh, d))
    scored.sort(key=lambda x: -x[0]["score"])
    cands = []
    for ts, yh, d in scored[:prefilter]:
        m = ts["metrics"]
        if fast:
            # no ML: a nominal positive forecast so the shared selection filter still applies
            fc = dict(predicted_return_pct=0.01, predicted_price=m["price"], quality_pass=True,
                      backtest=dict(best_dir_acc=50.0))
        else:
            try: fc = walk_forward_and_forecast(d, nc)
            except Exception: fc = None
            if fc is None: continue
        cands.append(dict(symbol=yh.replace(".NS", ""), yahoo=yh, current_price=m["price"], trader_score=ts["score"],
                          stop_loss=m["stop_loss"], target=m["target1"], risk_reward=m["risk_reward"], rsi=m["rsi"],
                          **fc))
    return cands


def select(cands, n):
    good = [c for c in cands if c["quality_pass"] and c["predicted_return_pct"] > 0 and c["rsi"] <= 80 and c["risk_reward"] >= 1.15]
    if len(good) < n:
        good = [c for c in cands if c["quality_pass"] and c["predicted_return_pct"] > 0] or good
    good.sort(key=rank_key)
    return good[:n]


def run(weeks=104, top=6, n_stocks=45, prefilter=15, fast=False, cost=bt.COST_PER_SIDE_PCT, log=print):
    t0 = time.time()
    tickers = pick_universe(n_stocks, log=log)
    stocks = load_history(tickers, log=log)
    idx = datafeed._yahoo_batch(["^NSEI", "^INDIAVIX"], period="5y")
    nifty = idx.get("^NSEI"); vix = idx.get("^INDIAVIX")
    if nifty is None: raise SystemExit("NIFTY history unavailable")
    nifty_close = nifty["Close"]
    # weekly origins: every HORIZON sessions on the NIFTY calendar, each with HORIZON forward bars
    sessions = list(nifty_close.index)
    origins = sessions[250:len(sessions) - HORIZON:HORIZON][-weeks:]
    log(f"[backtest] {len(origins)} weeks: {origins[0].date()} -> {origins[-1].date()} · top {top} of {len(stocks)} stocks · cost {cost}%/side · fast={fast}")

    base_weekly, gated_weekly, nifty_weekly, base_trades, gated_trades, weekly_rows = [], [], [], [], [], []
    rt = 2 * cost
    for k, t in enumerate(origins):
        reg = compute_regime(nifty_close[nifty_close.index <= t], vix["Close"][vix.index <= t] if vix is not None else None)
        regime_200 = bt.regime_on(nifty_close, t)
        cands = evaluate_week(stocks, nifty_close, t, prefilter, fast, log)
        picks = select(cands, top)
        # NIFTY same-horizon return
        fut_n = nifty_close[nifty_close.index > t].head(HORIZON)
        nifty_weekly.append((float(fut_n.iloc[-1]) / float(nifty_close.loc[t]) - 1) * 100 if len(fut_n) else 0.0)

        def trade(p, widen=1.0):
            q = dict(p); apply_stop_widen(q, widen)
            bars = stocks[p["yahoo"]]; fut = bars[bars.index > t].head(HORIZON)
            ex = bt.simulate_exit(fut, q["current_price"], q["stop_loss"], q["target"], HORIZON)
            if not ex: return None
            tr = bt.trade_from_pick(q, ex["exit"], regime=regime_200, mae_pct=ex["mae_pct"], mfe_pct=ex["mfe_pct"])
            tr.update(date=str(t.date()), reason=ex["reason"], bars_held=ex["bars_held"]); return tr

        b_tr = [x for x in (trade(p) for p in picks) if x]
        base_trades += b_tr
        base_weekly.append(float(np.mean([x["ret_pct"] - rt for x in b_tr])) if b_tr else 0.0)

        n_gated = min(top, int(reg["max_picks"]))
        g_tr = [x for x in (trade(p, reg["stop_widen"]) for p in picks[:n_gated]) if x]
        gated_trades += g_tr
        deploy = (1 - reg["cash_pct"]) * reg["size_mult"]
        gated_weekly.append(float(np.mean([x["ret_pct"] - rt for x in g_tr])) * deploy if g_tr else 0.0)
        weekly_rows.append(dict(date=str(t.date()), regime=reg["regime"], regime_200dma=regime_200, vix=reg["vix"],
                                picks=[p["symbol"] for p in picks], baseline_pct=round(base_weekly[-1], 3),
                                gated_pct=round(gated_weekly[-1], 3), nifty_pct=round(nifty_weekly[-1], 3)))
        if (k + 1) % 4 == 0 or k == len(origins) - 1:
            el = time.time() - t0
            log(f"[backtest] week {k+1}/{len(origins)} {t.date()} {reg['regime']:7s} picks={len(picks)} base={base_weekly[-1]:+.2f}% gated={gated_weekly[-1]:+.2f}% nifty={nifty_weekly[-1]:+.2f}% · {el/60:.1f} min")

    summary = dict(
        generated=date.today().isoformat(), params=dict(weeks=len(origins), top=top, stocks=len(stocks), prefilter=prefilter,
                                                         fast=fast, cost_per_side_pct=cost, horizon_bars=HORIZON),
        window=dict(start=str(origins[0].date()), end=str(origins[-1].date())),
        strategies=dict(
            baseline=dict(portfolio=bt.portfolio_metrics(base_weekly), trades=bt.compute_trade_stats(base_trades, cost)),
            regime_gated=dict(portfolio=bt.portfolio_metrics(gated_weekly), trades=bt.compute_trade_stats(gated_trades, cost)),
        ),
        nifty=bt.portfolio_metrics(nifty_weekly),
        regime_weeks={r: sum(1 for w in weekly_rows if w["regime"] == r) for r in ("bull", "neutral", "bear", "unknown")},
        weekly=weekly_rows,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    n = summary["nifty"]
    for name in ("baseline", "regime_gated"):
        s = summary["strategies"][name]; p, tr = s["portfolio"], s["trades"]
        log(f"\n{name.upper():13s} total {p.get('total_return_pct', 0):+.2f}%  DD {p.get('max_drawdown_pct', 0):.2f}%  Sharpe {p.get('sharpe')}  Calmar {p.get('calmar')}  | "
            f"trades {tr.get('n', 0)} win {tr.get('win_rate_pct')}% expR {tr.get('expectancy_R')} PF {tr.get('profit_factor')} payoff {tr.get('payoff_ratio')} "
            f"net/trade {tr.get('avg_return_net_pct')}% MAE {tr.get('avg_mae_pct')}% MFE {tr.get('avg_mfe_pct')}%")
        log(f"{'':13s} by 200-DMA regime: { {k: dict(n=v['n'], win=v['win_rate_pct'], net=v['avg_return_net_pct'], expR=v['expectancy_R']) for k, v in tr.get('by_regime', {}).items()} }")
    log(f"NIFTY         total {n.get('total_return_pct', 0):+.2f}%  DD {n.get('max_drawdown_pct', 0):.2f}%")
    log(f"wrote {OUT}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weeks", type=int, default=104)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--stocks", type=int, default=45)
    ap.add_argument("--prefilter", type=int, default=15, help="ML-evaluate only the top-K trader scores per week")
    ap.add_argument("--cost", type=float, default=bt.COST_PER_SIDE_PCT, help="%% per side")
    ap.add_argument("--fast", action="store_true", help="skip the ML walk-forward (trader_score ranking only)")
    a = ap.parse_args()
    run(weeks=a.weeks, top=a.top, n_stocks=a.stocks, prefilter=a.prefilter, fast=a.fast, cost=a.cost)
