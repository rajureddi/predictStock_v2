"""Enriches data/reports/latest.json with Time Machine Monte Carlo simulations and ORB status."""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app import simulation

def enrich_latest():
    path = ROOT / "data" / "reports" / "latest.json"
    if not path.exists():
        print("No latest.json found.")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    picks = data.get("picks", [])
    print(f"Enriching {len(picks)} picks with Time Machine simulation and ORB status...")
    for p in picks:
        sym = p.get("symbol")
        sim = simulation.simulate_pick(p, replays=1000)
        orb = simulation.check_orb_status(p)
        p["simulation"] = sim
        p["orb"] = orb
        verdict = sim.get("verdict") if sim else "N/A"
        win_prob = f"{sim.get('win_probability_pct')}%" if sim else "N/A"
        print(f"  {sym} ({p.get('exchange')}): Win Odds={win_prob}, Verdict={verdict}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    print("latest.json enriched successfully!")

if __name__ == "__main__":
    enrich_latest()

