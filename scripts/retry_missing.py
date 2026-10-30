#!/usr/bin/env python3
"""Retry pass: re-download universe tickers that produced no stage-1 result
(e.g. provider throttling during the first pass), score them, and merge into
the stage-1 checkpoint so a follow-up run_pipeline() uses the fuller set."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import universe as univ_mod, datafeed
from app.engine import trader_score
from app.pipeline import REPORTS, MIN_ROWS, MIN_TRADED_VALUE

ckpt = REPORTS / "stage1_checkpoint.json"
saved = json.loads(ckpt.read_text(encoding="utf-8")); results = saved["results"]
have = {r["yahoo"] for r in results}
uni = univ_mod.load_universe(); meta = {l["yahoo"]: l for l in uni["listings"]}
missing = [t for t in meta if t not in have]
print(f"missing: {len(missing)}")
nifty = datafeed.download_batch(["^NSEI"], period="1y").get("^NSEI")
nifty_close = nifty["Close"] if nifty is not None else None
added = 0
for i in range(0, len(missing), 25):
    batch = missing[i:i+25]
    data = datafeed.download_batch(batch, period="1y")
    for t, df in data.items():
        if len(df) < MIN_ROWS: continue
        ts = trader_score(df, nifty_close)
        if ts is None: continue
        m = ts["metrics"]; avg_vol = float(df["Volume"].tail(20).mean()); traded = m["price"]*avg_vol
        results.append(dict(yahoo=t, symbol=meta[t]["symbol"], name=meta[t]["name"], exchange=meta[t]["exchange"],
                            current_price=round(m["price"],2), trader_score=ts["score"], traded_value=round(traded),
                            liquid=bool(traded >= MIN_TRADED_VALUE and m["price"] >= 5),
                            rsi=round(m["rsi"],1), ret21_pct=round(m["ret21"]*100,2), reasons=ts["reasons"][:3]))
        added += 1
    if i % 500 == 0: print(f"  {i}/{len(missing)} retried, +{added}")
    time.sleep(1)
saved["results"] = results
ckpt.write_text(json.dumps(saved), encoding="utf-8")
print(f"retry added {added}; total with data now {len(results)}")
