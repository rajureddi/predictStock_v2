#!/usr/bin/env python3
"""MarketMind Pro weekly run: full-universe screen -> deep evaluation -> picks report.
Usage:  python scripts/weekly_run.py
Runs standalone; the website serves data/reports/latest.json."""
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.pipeline import run_pipeline

if __name__ == "__main__":
    r = run_pipeline()
    print(f"\n=== MarketMind Pro — week of {r['run_date']} -> target {r['target_date']} ===")
    print(f"Universe {r['universe_counts']} | stages {r['stage_counts']}")
    for p in r["picks"]:
        sim_odds = f"{p['simulation']['win_probability_pct']}%" if p.get("simulation") else "N/A"
        print(f"{p['symbol']} ({p['exchange']}) ₹{p['current_price']} -> ₹{p['predicted_price']} "
              f"({p['predicted_return_pct']:+.2f}%) acc {p['backtest']['best_dir_acc']}% | Sim Win: {sim_odds} SL ₹{p['stop_loss']} T ₹{p['target']}")
    if r.get("allocation"):
        print("Allocation:", r["allocation"])
