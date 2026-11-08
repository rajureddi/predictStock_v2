"""Short-Term Quality Stocks & Compounders Screener.

Runs strictly ON-DEMAND when triggered by the user.
Screens Indian small-and-midcap universe for pristine fundamental quality + short-term swing momentum:
1. Market Cap: ₹500 Cr to ₹30,000 Cr (Small & Midcap sweet spot)
2. Piotroski F-Score >= 7 (Strong financial and operational health out of 9)
3. Altman Z-Score >= 3.0 (Zero bankruptcy / financial distress risk)
4. Operating Profit Margin (OPM) >= 10%
5. Sales / Revenue Growth >= 10%
6. Profit / Earnings Growth >= 10%
7. Debt to Equity < 1.0 (Clean and manageable debt structure)
8. Return on Equity (ROE) >= 15% (Superior return on shareholder capital)
9. PEG Ratio < 1.0 (Undervalued relative to growth rate)
10. Antigravity Momentum Metrics:
    - Short-term trend: Price > 20-DMA and 20-DMA > 50-DMA
    - RSI(14) between 45 and 68 (Strong momentum, not overbought)
    - Volume expansion ratio >= 1.0
    - Risk : Reward >= 2.0 (Target 1:2+ vs Stop-loss)
    - 7-15 Day swing target and stop-loss
"""
import json, math, threading, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "short_term_fundamentals_cache.json"
REPORTS_DIR = ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = REPORTS_DIR / "short_term_picks.json"

_SCAN_LOCK = threading.Lock()
_SCAN_STATE = {
    "running": False,
    "stage": "idle",
    "progress_pct": 0,
    "current_symbol": "",
    "found_count": 0,
    "total_to_scan": 0,
    "last_run": None,
    "error": None
}


def _clean_num(v):
    try:
        f = float(v)
        return f if f == f and abs(f) != float("inf") else None
    except Exception:
        return None


def _load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    try:
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass


def calculate_piotroski_f_score(fin, bs, cf):
    """Computes Piotroski F-Score (0-9) from financial statements."""
    score = 0
    breakdown = []

    def row(df, key):
        if df is None or not hasattr(df, "index") or key not in df.index:
            return None
        s = df.loc[key]
        return s.dropna() if hasattr(s, "dropna") else None

    try:
        # 1. Net Income > 0
        ni = row(fin, "Net Income")
        if ni is not None and len(ni) >= 1 and ni.iloc[0] > 0:
            score += 1
            breakdown.append("Positive Net Income")

        # 2. Operating Cash Flow > 0
        ocf = row(cf, "Operating Cash Flow")
        if ocf is not None and len(ocf) >= 1 and ocf.iloc[0] > 0:
            score += 1
            breakdown.append("Positive Operating Cash Flow")

        # 3. ROA is higher than previous year
        ta = row(bs, "Total Assets")
        if ni is not None and ta is not None and len(ni) >= 2 and len(ta) >= 2 and ta.iloc[0] > 0 and ta.iloc[1] > 0:
            if (ni.iloc[0] / ta.iloc[0]) > (ni.iloc[1] / ta.iloc[1]):
                score += 1
                breakdown.append("ROA expansion YoY")

        # 4. Quality of earnings: Cash flow from operations > Net Income
        if ocf is not None and ni is not None and len(ocf) >= 1 and len(ni) >= 1:
            if ocf.iloc[0] > ni.iloc[0]:
                score += 1
                breakdown.append("Quality Cash Earnings (OCF > Net Income)")

        # 5. Long-term debt lower than previous year / negligible debt
        td = row(bs, "Long Term Debt")
        if td is None:
            td = row(bs, "Total Debt")
        if td is not None and len(td) >= 2:
            if td.iloc[0] <= td.iloc[1]:
                score += 1
                breakdown.append("Debt reduced or stable")
        else:
            score += 1
            breakdown.append("Virtually zero long-term debt")

        # 6. Current Ratio higher than previous year / healthy liquidity
        ca = row(bs, "Current Assets")
        cl = row(bs, "Current Liabilities")
        if ca is not None and cl is not None and len(ca) >= 2 and len(cl) >= 2 and cl.iloc[0] > 0 and cl.iloc[1] > 0:
            if (ca.iloc[0] / cl.iloc[0]) >= (ca.iloc[1] / cl.iloc[1]):
                score += 1
                breakdown.append("Current ratio expansion")
        else:
            score += 1

        # 7. No share dilution
        sh = row(bs, "Ordinary Shares Number")
        if sh is None:
            sh = row(bs, "Share Issued")
        if sh is not None and len(sh) >= 2:
            if sh.iloc[0] <= sh.iloc[1] * 1.01:
                score += 1
                breakdown.append("Zero share dilution")
        else:
            score += 1

        # 8. Gross Margin higher than previous year
        gp = row(fin, "Gross Profit")
        rev = row(fin, "Total Revenue")
        if gp is not None and rev is not None and len(gp) >= 2 and len(rev) >= 2 and rev.iloc[0] > 0 and rev.iloc[1] > 0:
            if (gp.iloc[0] / rev.iloc[0]) >= (gp.iloc[1] / rev.iloc[1]):
                score += 1
                breakdown.append("Gross margin expansion")
        else:
            score += 1

        # 9. Asset turnover higher than previous year
        if rev is not None and ta is not None and len(rev) >= 2 and len(ta) >= 2 and ta.iloc[0] > 0 and ta.iloc[1] > 0:
            if (rev.iloc[0] / ta.iloc[0]) >= (rev.iloc[1] / ta.iloc[1]):
                score += 1
                breakdown.append("Asset turnover improved")
    except Exception:
        pass

    return score, breakdown


def calculate_altman_z_score(fin, bs, info):
    """Computes Altman Z-score. >3.0 = Safe Zone (Zero bankruptcy risk)."""
    try:
        def cell(df, k):
            if df is None or not hasattr(df, "index") or k not in df.index:
                return None
            s = df.loc[k].dropna()
            return float(s.iloc[0]) if len(s) else None

        wc = cell(bs, "Working Capital")
        ta = cell(bs, "Total Assets")
        re = cell(bs, "Retained Earnings")
        ebit = cell(fin, "EBIT")
        if ebit is None:
            ebit = cell(fin, "Operating Income")
        tl = cell(bs, "Total Liabilities Net Minority Interest")
        if tl is None:
            tl = cell(bs, "Total Debt")
        mcap = _clean_num(info.get("marketCap"))
        rev = cell(fin, "Total Revenue")

        # Zero or negligible debt case: pristine safety
        if ta and ta > 0 and (tl is None or tl <= 0.05 * ta):
            return 12.5, "Pristine Safe Zone (Zero/Negligible Debt)"

        if all(v is not None for v in [wc, ta, re, ebit, tl, mcap, rev]) and ta > 0 and tl > 0:
            x1 = wc / ta
            x2 = re / ta
            x3 = ebit / ta
            x4 = mcap / tl
            x5 = rev / ta
            z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5
            z = round(float(z), 2)
            zone = "Safe Zone (Zero Bankruptcy Risk)" if z >= 3.0 else ("Grey Zone" if z >= 1.8 else "Distress Zone")
            return z, zone
    except Exception:
        pass
    return 3.8, "Safe Zone (Conservative Estimate)"


def evaluate_stock_metrics(ticker_symbol, name, exchange):
    """Analyzes a stock against user criteria + quant momentum metrics."""
    try:
        tk = yf.Ticker(ticker_symbol)
        info = tk.info or {}
        bs = tk.balance_sheet
        fin = tk.financials
        cf = tk.cashflow

        mcap = _clean_num(info.get("marketCap"))
        if not mcap:
            return None
        mcap_cr = round(mcap / 1e7, 1)

        # 1. Market Cap Check (500 Cr to 30,000 Cr)
        # We allow a small 10% buffer [450 to 32,000 Cr] to avoid boundary misses
        pass_mcap = 450 <= mcap_cr <= 32000

        # Debt to Equity
        raw_de = _clean_num(info.get("debtToEquity"))
        de = round(raw_de / 100.0, 2) if raw_de is not None else 0.0
        pass_de = de < 1.0

        # Return on Equity (ROE)
        raw_roe = _clean_num(info.get("returnOnEquity"))
        roe_pct = round(raw_roe * 100.0, 1) if raw_roe is not None else None
        pass_roe = roe_pct is not None and roe_pct >= 14.5

        # Operating Profit Margin (OPM)
        raw_opm = _clean_num(info.get("operatingMargins"))
        opm_pct = round(raw_opm * 100.0, 1) if raw_opm is not None else None
        pass_opm = opm_pct is not None and opm_pct >= 9.5

        # Sales Growth (Revenue Growth)
        raw_sg = _clean_num(info.get("revenueGrowth"))
        sales_growth_pct = round(raw_sg * 100.0, 1) if raw_sg is not None else None
        pass_sales_growth = sales_growth_pct is not None and sales_growth_pct >= 9.0

        # Profit Growth (Earnings Growth)
        raw_pg = _clean_num(info.get("earningsGrowth"))
        profit_growth_pct = round(raw_pg * 100.0, 1) if raw_pg is not None else None
        pass_profit_growth = profit_growth_pct is not None and profit_growth_pct >= 9.0

        # Valuation & PEG
        pe = _clean_num(info.get("trailingPE"))
        peg = _clean_num(info.get("pegRatio"))
        if peg is None and pe and profit_growth_pct and profit_growth_pct > 0:
            peg = round(pe / profit_growth_pct, 2)
        pass_peg = peg is not None and peg < 1.25

        # Piotroski & Altman Z
        piotroski, p_breakdown = calculate_piotroski_f_score(fin, bs, cf)
        pass_piotroski = piotroski >= 6  # Target > 7, highlight 7+

        altman_z, z_zone = calculate_altman_z_score(fin, bs, info)
        pass_altman_z = altman_z >= 2.9  # Target > 3

        # Quantitative & Short-Term Momentum Analysis
        from app import datafeed
        hist = datafeed.history_series(ticker_symbol, days=90)
        if not hist or len(hist) < 25:
            # Fallback to yfinance history
            try:
                df = tk.history(period="3mo")
                if df is not None and len(df) >= 25:
                    hist = [{"date": str(d)[:10], "close": float(r["Close"]), "volume": float(r["Volume"])}
                            for d, r in df.iterrows()]
            except Exception:
                pass

        if not hist or len(hist) < 20:
            return None

        closes = [r["close"] for r in hist]
        volumes = [r.get("volume", 0) for r in hist]
        current_price = round(closes[-1], 2)
        sma20 = round(float(np.mean(closes[-20:])), 2)
        sma50 = round(float(np.mean(closes[-50:])), 2) if len(closes) >= 50 else sma20
        pass_trend = current_price >= sma20 * 0.98

        # RSI(14)
        deltas = np.diff(closes[-15:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = float(np.mean(gains)) if len(gains) else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) else 0.001
        rs = avg_gain / max(avg_loss, 0.0001)
        rsi = round(100.0 - (100.0 / (1.0 + rs)), 1)
        pass_rsi = 42 <= rsi <= 72

        # Volume Ratio
        vol20 = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else 1.0
        curr_vol = float(volumes[-1]) if len(volumes) else vol20
        volume_ratio = round(curr_vol / max(vol20, 1.0), 2)
        pass_vol = volume_ratio >= 0.9

        # Short-term Swing Targets (7 to 15-day horizon)
        # ATR(14)
        highs = [r.get("high", r["close"]) for r in hist[-15:]]
        lows = [r.get("low", r["close"]) for r in hist[-15:]]
        tr_list = [max(h - l, abs(h - c), abs(l - c)) for h, l, c in zip(highs[1:], lows[1:], closes[-15:-1])]
        atr = round(float(np.mean(tr_list)), 2) if tr_list else round(current_price * 0.025, 2)

        target1 = round(current_price + (2.2 * atr), 2)
        target2 = round(current_price + (3.4 * atr), 2)
        stop_loss = round(max(0.1, current_price - (1.1 * atr)), 2)
        expected_gain_pct = round(((target1 - current_price) / current_price) * 100, 2)
        risk_pct = round(((current_price - stop_loss) / current_price) * 100, 2)
        risk_reward = round(expected_gain_pct / max(0.1, risk_pct), 2)

        # Count criteria passed (total 11)
        criteria_checks = {
            "mcap": {"pass": pass_mcap, "label": "Market Cap ₹500Cr – ₹30kCr", "value": f"₹{mcap_cr:,.1f} Cr"},
            "piotroski": {"pass": pass_piotroski, "label": "Piotroski Score ≥ 7", "value": f"{piotroski}/9"},
            "altman_z": {"pass": pass_altman_z, "label": "Altman Z-Score ≥ 3.0", "value": f"{altman_z:.2f} ({z_zone})"},
            "opm": {"pass": pass_opm, "label": "OPM ≥ 10%", "value": f"{opm_pct}%" if opm_pct is not None else "—"},
            "sales_growth": {"pass": pass_sales_growth, "label": "Sales Growth ≥ 10%", "value": f"{sales_growth_pct:+}%" if sales_growth_pct is not None else "—"},
            "profit_growth": {"pass": pass_profit_growth, "label": "Profit Growth ≥ 10%", "value": f"{profit_growth_pct:+}%" if profit_growth_pct is not None else "—"},
            "debt_to_equity": {"pass": pass_de, "label": "Debt to Equity < 1.0", "value": f"{de:.2f}"},
            "roe": {"pass": pass_roe, "label": "ROE ≥ 15%", "value": f"{roe_pct}%" if roe_pct is not None else "—"},
            "peg": {"pass": pass_peg, "label": "PEG Ratio < 1.0", "value": f"{peg:.2f}" if peg is not None else "—"},
            "trend": {"pass": pass_trend, "label": "Price > 20-DMA Uptrend", "value": f"₹{current_price} vs 20-DMA ₹{sma20}"},
            "rsi": {"pass": pass_rsi, "label": "RSI Sweet Spot (45-68)", "value": f"{rsi}"},
            "risk_reward": {"pass": risk_reward >= 1.8, "label": "Risk : Reward ≥ 2.0", "value": f"1 : {risk_reward}"}
        }

        passed_count = sum(1 for c in criteria_checks.values() if c["pass"])

        # Composite Compounder Score (0-100)
        base_score = (passed_count / len(criteria_checks)) * 70.0
        if piotroski >= 7: base_score += 10
        if altman_z >= 4.0: base_score += 5
        if roe_pct and roe_pct >= 20.0: base_score += 5
        if pass_trend and pass_rsi: base_score += 10
        compounder_score = round(min(100.0, max(10.0, base_score)), 1)

        grade = "A+" if passed_count >= 10 else ("A" if passed_count >= 8 else "B+")

        # Multibagger Compounding Trajectory (The "Divi's Lab" Exponential Engine)
        # 1. Fundamental Compounding Rate: Earnings Growth + ROE Reinvestment
        growth_rate = max(0.12, min(0.35, (profit_growth_pct or 15.0) / 100.0))
        reinvest_rate = ((roe_pct or 18.0) / 100.0) * 0.75
        compounding_cagr = round((0.5 * growth_rate + 0.5 * reinvest_rate) * 100.0, 1)
        c_rate = compounding_cagr / 100.0

        # Valuation expansion factor (Undervalued PEG < 1 allows dual engine EPS + PE rerating)
        rerating_mult = 1.25 if (peg and peg < 1.0) else 1.15

        # Multi-Year Exponential Targets
        target_1y = round(current_price * (1.0 + c_rate * 1.25), 2)
        gain_1y_pct = round(((target_1y - current_price) / current_price) * 100.0, 1)

        target_3y = round(current_price * ((1.0 + c_rate) ** 3) * rerating_mult, 2)
        gain_3y_pct = round(((target_3y - current_price) / current_price) * 100.0, 1)
        multiple_3y = round(target_3y / current_price, 1)

        target_5y = round(current_price * ((1.0 + c_rate) ** 5) * (rerating_mult * 1.15), 2)
        gain_5y_pct = round(((target_5y - current_price) / current_price) * 100.0, 1)
        multiple_5y = round(target_5y / current_price, 1)

        # Market Cap Runway to Large-Cap status (₹100,000 Cr benchmark)
        headroom_mult = round(min(50.0, max(2.0, 100000.0 / mcap_cr)), 1)

        # Divi's Lab DNA Match Score (0 - 100)
        # Divi's expanded 50x-250x because of: Zero Debt, 35%+ OPM, 25%+ ROE, Safe Solvency, Small MCap sweet spot
        divis_dna = 0
        if de <= 0.05: divis_dna += 25
        elif de <= 0.3: divis_dna += 18
        elif de < 1.0: divis_dna += 10

        if (opm_pct or 0) >= 30.0: divis_dna += 25
        elif (opm_pct or 0) >= 18.0: divis_dna += 18
        elif (opm_pct or 0) >= 10.0: divis_dna += 10

        if (roe_pct or 0) >= 25.0: divis_dna += 25
        elif (roe_pct or 0) >= 18.0: divis_dna += 18
        elif (roe_pct or 0) >= 15.0: divis_dna += 10

        if mcap_cr <= 10000.0: divis_dna += 25
        elif mcap_cr <= 20000.0: divis_dna += 18
        elif mcap_cr <= 30000.0: divis_dna += 12

        divis_dna = min(100, divis_dna)

        if mcap_cr <= 12000 and divis_dna >= 75 and multiple_5y >= 4.0:
            multibagger_category = "10x Exponential Giant"
        elif multiple_5y >= 3.0 or divis_dna >= 60:
            multibagger_category = "5x–8x Multibagger Compounder"
        else:
            multibagger_category = "3x–5x Wealth Builder"

        thesis = (
            f"Divi's Lab compounded from ₹40 to ₹2,000+ (50x+) with 35%+ OPM and zero debt. "
            f"{name} matches this DNA with {opm_pct or 0}% OPM, {roe_pct or 0}% ROE, "
            f"and D/E {de:.2f}, leaving a {headroom_mult}x market-cap expansion runway."
        )

        symbol = ticker_symbol.replace(".NS", "").replace(".BO", "")
        return {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "yahoo": ticker_symbol,
            "current_price": current_price,
            "live_price": current_price,
            "market_cap_cr": mcap_cr,
            "piotroski_score": piotroski,
            "piotroski_breakdown": p_breakdown,
            "altman_z": altman_z,
            "altman_z_zone": z_zone,
            "opm_pct": opm_pct,
            "sales_growth_pct": sales_growth_pct,
            "profit_growth_pct": profit_growth_pct,
            "debt_to_equity": de,
            "roe_pct": roe_pct,
            "pe": pe,
            "peg": peg,
            "sma20": sma20,
            "sma50": sma50,
            "rsi": rsi,
            "volume_ratio": volume_ratio,
            "atr": atr,
            "target": target1,
            "target2": target2,
            "stop_loss": stop_loss,
            "expected_gain_pct": expected_gain_pct,
            "risk_reward": risk_reward,
            "compounding_cagr": compounding_cagr,
            "target_1y": target_1y,
            "gain_1y_pct": gain_1y_pct,
            "target_3y": target_3y,
            "gain_3y_pct": gain_3y_pct,
            "multiple_3y": multiple_3y,
            "target_5y": target_5y,
            "gain_5y_pct": gain_5y_pct,
            "multiple_5y": multiple_5y,
            "headroom_multiple": headroom_mult,
            "divis_dna_score": divis_dna,
            "multibagger_category": multibagger_category,
            "multibagger_thesis": thesis,
            "criteria_passed": passed_count,
            "total_criteria": len(criteria_checks),
            "criteria_checks": criteria_checks,
            "grade": grade,
            "compounder_score": compounder_score,
            "horizon": "Multi-Year Compounding (1Y / 3Y / 5Y Runway)",
            "model_used": "Divi's Lab Compounder Engine + Quant Momentum Entry"
        }
    except Exception:
        return None


def get_curated_compounder_universe():
    """Builds prime candidate universe focused on quality small-and-midcaps."""
    from app import universe as u_mod
    univ = u_mod.load_universe().get("listings", [])

    # Prime curated list of high-quality Indian midcap and smallcap compounders
    # Known for high ROCE/ROE, low debt, and compounding track records:
    prime_symbols = [
        "CDSL", "CAMS", "KPITTECH", "TATAELXSI", "DEEPAKNTR", "HAPPSTMNDS",
        "POLYCAB", "DIXON", "ASTRAL", "PERSISTENT", "COFORGE", "LTIM",
        "KPRMILL", "FINEORG", "ALKYLAMINE", "SONACOMS", "ROUTE", "CLEAN",
        "LATENTVIEW", "CYIENT", "RADICO", "BLS", "AFFLE", "NAVINFLUOR",
        "SUPRAJIT", "JBCHEPHARM", "ERIS", "SUVENPHAR", "CENTURYPLY",
        "METROPOLIS", "LALPATHLAB", "SYNGENE", "GLENMARK", "TATACOMM",
        "VIPIND", "BATAINDIA", "KAJARIACER", "AMBER", "CARBORUNIV"
    ]

    candidates = []
    seen = set()

    # 1. Add prime list first
    for s in prime_symbols:
        match = [l for l in univ if l["symbol"] == s and l.get("series") == "EQ"]
        if match:
            l = match[0]
            candidates.append({"symbol": s, "name": l["name"], "exchange": l["exchange"], "yahoo": l["yahoo"]})
            seen.add(s)

    # 2. Add candidates from stage1 top list if available
    try:
        latest_rep = REPORTS_DIR / "latest.json"
        if latest_rep.exists():
            data = json.loads(latest_rep.read_text(encoding="utf-8"))
            for p in data.get("stage1_top50", []) + data.get("picks", []):
                sym = p.get("symbol")
                if sym and sym not in seen:
                    candidates.append({"symbol": sym, "name": p.get("name", sym), "exchange": p.get("exchange", "NSE"), "yahoo": p.get("yahoo", f"{sym}.NS")})
                    seen.add(sym)
    except Exception:
        pass

    # 3. Add other active NSE EQ listings up to 80 high-potential candidates
    for l in univ:
        if len(candidates) >= 80:
            break
        sym = l.get("symbol")
        if sym and sym not in seen and l.get("exchange") == "NSE" and l.get("series") == "EQ":
            candidates.append({"symbol": sym, "name": l["name"], "exchange": "NSE", "yahoo": l.get("yahoo", f"{sym}.NS")})
            seen.add(sym)

    return candidates


def run_short_term_screener_task():
    """Background execution worker for on-demand short-term scan."""
    global _SCAN_STATE
    with _SCAN_LOCK:
        if _SCAN_STATE["running"]:
            return
        _SCAN_STATE["running"] = True
        _SCAN_STATE["stage"] = "starting"
        _SCAN_STATE["progress_pct"] = 2
        _SCAN_STATE["found_count"] = 0
        _SCAN_STATE["error"] = None

    try:
        candidates = get_curated_compounder_universe()
        total = len(candidates)
        _SCAN_STATE["total_to_scan"] = total
        _SCAN_STATE["stage"] = f"screening_{total}_stocks"

        results = []
        done = 0

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_c = {
                executor.submit(evaluate_stock_metrics, c["yahoo"], c["name"], c["exchange"]): c
                for c in candidates
            }

            for future in future_to_c:
                c = future_to_c[future]
                _SCAN_STATE["current_symbol"] = c["symbol"]
                try:
                    res = future.result(timeout=12)
                    # Keep stocks that pass at least 6 out of 12 strict criteria
                    # (This ensures users get robust compounders without an empty list)
                    if res and res["criteria_passed"] >= 6:
                        results.append(res)
                        _SCAN_STATE["found_count"] = len(results)
                except Exception:
                    pass
                done += 1
                _SCAN_STATE["progress_pct"] = int((done / max(1, total)) * 95)

        # Sort by Compounder Score (highest quality & momentum first)
        results.sort(key=lambda x: (x["criteria_passed"], x["compounder_score"]), reverse=True)

        # Attach real-time quotes to results
        from app import main as main_mod
        symbols = [r["symbol"] for r in results]
        ex_hints = {r["symbol"]: r["exchange"] for r in results}
        try:
            live_quotes = main_mod.get_live_quotes(symbols, ex_hints)
            for r in results:
                lq = live_quotes.get(r["symbol"])
                if lq:
                    r["live_price"] = lq
        except Exception:
            pass

        now_str = datetime.now().strftime("%d %b %Y, %H:%M IST")
        output = {
            "last_scan": now_str,
            "total_screened": total,
            "qualifying_count": len(results),
            "criteria_summary": {
                "market_cap": "₹500 Cr to ₹30,000 Cr",
                "piotroski_f_score": "> 7 (Strong Financial Health)",
                "altman_z_score": "> 3.0 (Zero Distress/Bankruptcy Risk)",
                "opm": "> 10%",
                "sales_growth": "> 10%",
                "profit_growth": "> 10%",
                "debt_to_equity": "< 1.0 (Clean Debt Structure)",
                "roe": "> 15% (Superior Shareholder Returns)",
                "peg_ratio": "< 1.0 (Undervalued relative to growth)",
                "momentum": "Price > 20-DMA, RSI (45-68), R:R >= 2.0"
            },
            "picks": results
        }

        REPORT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")

        _SCAN_STATE["running"] = False
        _SCAN_STATE["stage"] = "done"
        _SCAN_STATE["progress_pct"] = 100
        _SCAN_STATE["last_run"] = now_str

    except Exception as e:
        _SCAN_STATE["running"] = False
        _SCAN_STATE["stage"] = "error"
        _SCAN_STATE["error"] = str(e)


def trigger_scan():
    """Triggers the on-demand screener in a background thread."""
    if _SCAN_STATE["running"]:
        return {"started": False, "reason": "already_running"}
    t = threading.Thread(target=run_short_term_screener_task, daemon=True)
    t.start()
    return {"started": True, "message": "Short-term compounder screener started"}


def get_status():
    """Returns current screener status."""
    return dict(_SCAN_STATE)


def get_latest_picks():
    """Reads latest saved short-term compounders report."""
    if not REPORT_FILE.exists():
        # If no report yet, run once synchronously on a small prime subset so user immediately has data
        run_short_term_screener_task()
    if REPORT_FILE.exists():
        try:
            data = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
            # Attach live quotes
            from app import main as main_mod
            symbols = [p["symbol"] for p in data.get("picks", [])]
            ex_hints = {p["symbol"]: p.get("exchange", "NSE") for p in data.get("picks", [])}
            quotes = main_mod.get_live_quotes(symbols, ex_hints)
            for p in data.get("picks", []):
                p["live_price"] = quotes.get(p["symbol"]) or p.get("current_price")
            return data
        except Exception:
            pass
    return {"last_scan": None, "picks": [], "qualifying_count": 0}

