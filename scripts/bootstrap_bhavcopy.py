#!/usr/bin/env python3
"""One-time (resumable) Bhavcopy history bootstrap: download daily NSE+BSE
bhavcopy files for the last ~13 months and build the merged history panels.

Re-running is safe: dates already downloaded (or known-missing) are skipped.
Usage: python scripts/bootstrap_bhavcopy.py [months_back]
"""
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import bhavcopy, universe as univ_mod


def main():
    months = float(sys.argv[1]) if len(sys.argv) > 1 else 13
    start = date.today() - timedelta(days=int(months * 30.5))
    print(f"Bootstrap window: {start} .. {date.today()}", flush=True)
    for ex in ("nse", "bse"):
        got, att = bhavcopy.download_range(ex, start, date.today())
        print(f"{ex}: +{got} files ({att} attempted), total on disk: "
              f"{len(bhavcopy.existing_dates(ex))}", flush=True)
    uni = univ_mod.load_universe()
    meta = bhavcopy.build_panels(uni)
    print("Panel meta:", meta, flush=True)


if __name__ == "__main__":
    main()
