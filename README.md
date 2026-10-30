# MarketMind Pro

Professional-trader-style Indian stock prediction. Every week it screens the
**entire Indian market (NSE + BSE, ~7,987 listings)**, reads each stock the way
an experienced trader would — candlestick patterns, trend, momentum, volume,
delivery %, support/resistance, relative strength vs NIFTY — then predicts the
price **7 calendar days ahead** and picks only the best **5–7 stocks** that
pass a hard quality gate, a fundamentals check, a news veto and your budget.

## V2 — what's new
- **Official exchange data first (Bhavcopy).** Daily NSE full bhavcopy and
  BSE UDiFF bhavcopy are downloaded into `data/bhavcopy/raw/` and merged into
  history panels (`data/history/{nse,bse}_panel.csv.gz`, ~13 months). This
  covers BSE scrips Yahoo doesn't carry (BSE with-data went from ~0 usable
  to ~5,000) and adds **delivery quantity / delivery %** (NSE) — a
  genuine-buying signal in the Trader Score (+3 for ≥50% delivery on an up
  day; −2 for <25% delivery on a big up day). Yahoo remains a fallback and
  extends stage-2 history to 2 years (local data wins on overlapping dates).
  Bootstrap/refresh: `python scripts/bootstrap_bhavcopy.py`
  (resumable); every pipeline run tops up missing days automatically.
- **Fundamentals check (stage 2).** yfinance `.info` (cached 7 days in
  `data/fundamentals_cache.json`) → transparent 0–100 score + flags
  (ROE, debt/equity, earnings & revenue growth, P/E). The score nudges the
  final ranking ((score−50)×0.1); a **severe red flag (D/E > 3 AND earnings
  shrinking) demotes** a stock out of the final 7 when enough clean picks
  exist — demoted stocks are listed in the report (`red_flag_demoted`).
- **News check + veto (final candidates).** Google News RSS headlines from
  the last 14 days, keyword sentiment (Positive/Neutral/Negative), and a
  **hard veto**: any headline about fraud, default, insolvency, a SEBI ban
  or penalty, a raid or an arrest excludes the stock (when ≥7 clean
  candidates remain) and is listed openly in the report's `vetoed` section
  and on the website — never silently.
- **Institutional dark-terminal UI.** Navy + gold glass theme, Space Grotesk
  numerals, week-summary stat strip (incl. per-exchange data coverage),
  pick cards with a trader-score radial, likely-range bar
  (stop-loss → range → now → predicted → target), 90-day price chart with
  the prediction drawn in (`GET /api/prices/{symbol}`), fundamentals and
  news panels, a visible "Excluded by safety checks" section, searchable /
  sortable scanned-stocks table, and hit/miss badges on Past Weeks.

## How a pick is made (no black box, no promised accuracy)
1. **Stage 1 — full screen.** Official Bhavcopy OHLCV for every listing
   (Yahoo fallback). Liquidity filter (≥ ₹50 lakh average daily traded
   value) + Trader Score (patterns, EMA trend, ADX, RSI, MACD, stochastic,
   volume surge, OBV, delivery %, breakout/levels, relative strength)
   with plain-language reasons.
2. **Stage 2 — deep evaluation (top ~150).** Per-stock ML model
   (HistGradientBoosting) + trend/drift model, blended by backtest skill.
   **Walk-forward backtest** on the stock's own history gives measured
   directional accuracy % and price MAPE. Fundamentals are attached here.
3. **Quality gate.** A stock can only be a final pick if its best model
   **beat the naive baseline** in that backtest and the predicted return is
   positive. Then fundamentals ranking + red-flag demotion, then the news
   veto. Accuracy shown is measured — never invented or promised.

## Run it — from the website (no terminal needed)
Open the website and click **🔍 Scan Market** on the "This Week's Picks"
page. The scan runs in the background (`POST /api/scan/start`), the page
shows live progress (`GET /api/scan/status` — stage-1 batch X of 80, stocks
checked, liquidity passes, then the stage-2 deep-analysis state), and the
new predicted stocks appear automatically when the scan completes. Only one
scan can run at a time: if a scan is already running (website, terminal, or
the Monday cron), the button reports that instead of starting a second one.
All loading states use the `thinking-orbs` Orb animation (no plain
spinners): connecting on first page load, searching during stage 1, solving
during stage 2 deep analysis, a small inline orb while the budget saves,
and a calm breathing orb on the empty picks state.
The terminal command still works too (full pipeline, ~30-60 min, resumable):
```
python scripts/weekly_run.py
```
Backend (port 8001) and website (port 5174):
```
uvicorn app.main:app --app-dir backend --port 8001   # API
cd frontend && npm run dev                           # website http://localhost:5174
```
Tests: `python -m pytest backend/tests -q` · Frontend build: `cd frontend && npm run build`

### Windows setup (PowerShell)
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd frontend; npm install; cd ..
python scripts\bootstrap_bhavcopy.py     # one-time official-data history download
uvicorn app.main:app --app-dir backend --port 8001
cd frontend; npm run dev                 # then open http://localhost:5174
```
The code is Windows-checked: the scanner launches with the same Python that
runs the backend (`sys.executable`), process checks use the Win32 API (never
`os.kill(pid, 0)` — on Windows that is Ctrl+C), and all file I/O is UTF-8.

## Budget
Enter your budget **on the website** (This Week's Picks page). It is saved
server-side in `data/screen_config.json` and the page immediately shows whole
shares per pick, invested amount, leftover, expected value and expected
profit. No budget = ranked picks without share counts.

## Weekly Monday report
Cron job **marketmind-pro-weekly** runs every Monday ~07:07 IST: it runs
`scripts/weekly_run.py` and delivers the full picks report in chat (Gmail is
not connected). Reports live in `data/reports/` (`latest.json` + dated files);
the "Past Weeks" page fills in actual prices as target dates pass.

## Data & universe notes
- Universe: NSE official equity list (nsearchives.nseindia.com EQUITY_L.csv,
  all series = 2,613) + BSE listings (5,374) = **7,987 listings**.
  bseindia.com's own API returns HTTP 403 to programmatic access from this
  environment, so the BSE list is taken from the published BSE instrument
  master (Upstox exchange file), which carries the official BSE scrip codes;
  debt/bond instruments are filtered out.
- Prices: **NSE/BSE Bhavcopy (official exchange EOD) primary**, Yahoo
  Finance daily OHLCV (`.NS` / `.BO`, index `^NSEI`) as fallback/extender.
  NSE source: `nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv`
  (includes delivery qty/%). BSE source: the UDiFF daily CSV at
  `bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_YYYYMMDD_F_0000.CSV`
  (the `.zip` variant serves an HTML block page — use the direct `.CSV`).
  BSE UDiFF carries no delivery columns, so delivery % is NSE-only.
- Target date = run date + 7 calendar days; the forecast horizon is
  5 trading days. Predictions are analysis, not investment advice.
