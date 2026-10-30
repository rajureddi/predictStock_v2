# Day Trader Skills — MarketMind Pro

11 AI agent skills from [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill),
installed into this project for Indian market day-trading workflows.

## Setup

1. Edit `trader/config.json`:
   - Set `"sec_user_agent": "Your Name you@email.com"` (required for SEC/EDGAR tools)
   - Set `"budget"` to your actual paper-trading budget
   - Keep `"paper": true` until you're ready for live trading

2. Python 3.8+ required. No pip install needed — all tools use stdlib + free public APIs.

## Skills (invoke with `/trader-*`)

| Skill | Script | What it does |
|-------|--------|-------------|
| `/trader-scanner` | `scan.py` | Scans charts for ORB/flag/oversold setups |
| `/trader-news` | `news.py` | Tracks breaking news, Yahoo headlines, 8-K filings |
| `/trader-entry` | `entry.py` | Watches a setup bar-by-bar, times your entry |
| `/trader-exit` | `exit.py` | Sets stop and profit target before entry |
| `/trader-timemachine` | `timemachine.py` | Replays 10,000 sessions + historical matches |
| `/trader-risk` | `check.py` | Blocks trades that exceed your limits |
| `/trader-budget` | `size.py` | Sizes position to budget + max loss rules |
| `/trader-broker` | `ticket.py` | Routes orders (paper by default, requires your yes) |
| `/trader-alerts` | `alerts.py` | Price, stop, and bell alerts |
| `/trader-analyst` | `facts.py` | Earnings reports and fundamental changes |
| `/trader-pelosi` | `ptr.py` | Congress stock-trade disclosures (House Clerk) |

## CLI usage (direct Python)

```bash
# Scan NSE/BSE charts (adapt ticker list for Indian stocks)
python trader/scan.py universe

# Check a ticker's news
python trader/news.py --tickers RELIANCE.NS --hours 12

# Time Machine — replay before risking capital
python trader/timemachine.py run --write

# Check risk limits
python trader/check.py

# Alerts
python trader/alerts.py check
```

## Workflow order

```
scanner → news → entry → exit → timemachine → budget → risk → broker
alerts: stop, target, flat by close     (while position is open)
news / analyst / pelosi                 (on a schedule)
```

> **Paper trading first.** `"paper": true` is the default. Nothing executes without your explicit yes.

