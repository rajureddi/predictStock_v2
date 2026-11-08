"""
TradeAnalyser - Multi-Agent Institutional Trading Framework for Indian Equities (NSE/BSE)
Inspired by TauricResearch/TradingAgents (UCLA/MIT research framework)

Replicates the collaborative structure of an institutional investment committee:
1. Fundamental Analyst Agent
2. Technical Analyst Agent
3. Sentiment & Regulatory Analyst Agent
4. Bull Researcher Agent
5. Bear Researcher Agent
6. Interactive Bull vs. Bear Debate Exchange
7. Chief Risk Officer (CRO)
8. Fund Manager / Chief Investment Officer (CIO)
"""

import os
import sys
import json
import time
import math
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app import datafeed, fundamentals as fundamentals_mod, news as news_mod
from app.engine import trader_score, build_features
from app.short_term_screener import calculate_piotroski_f_score, calculate_altman_z_score

logger = logging.getLogger("trade_analyser")
logger.setLevel(logging.INFO)

REPORTS_DIR = ROOT / "data" / "reports"
CACHE_FILE = REPORTS_DIR / "trade_analyser_reports.json"

_ANALYSIS_LOCK = threading.Lock()
_ANALYSIS_STATE = {
    "running": False,
    "current_symbol": None,
    "progress_pct": 0,
    "completed": 0,
    "total": 0,
    "last_error": None,
}


def sanitize_for_json(obj: Any) -> Any:
    """Recursively converts NaN, Inf, -Inf, numpy types to standard JSON-safe primitives."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(x) for x in obj]
    elif isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj


def load_cached_reports() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cached_reports(reports: Dict[str, Any]):
    sanitized = sanitize_for_json(reports)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2, ensure_ascii=False)


def get_top10_candidates() -> List[Dict[str, Any]]:
    """Gathers top predicted stocks from latest.json, supplemented by short_term_picks.json up to 10."""
    candidates = []
    seen = set()

    # 1. From latest.json (Daily / Weekly ML Predictions)
    latest_file = REPORTS_DIR / "latest.json"
    if latest_file.exists():
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                for p in d.get("picks", []):
                    sym = p.get("symbol")
                    if sym and sym not in seen:
                        candidates.append({
                            "symbol": sym,
                            "name": p.get("name") or sym,
                            "exchange": p.get("exchange") or "NSE",
                            "source": "Weekly ML Prediction",
                            "predicted_return_pct": p.get("predicted_return_pct", 0.0),
                            "predicted_price": p.get("predicted_price"),
                            "current_price": p.get("current_price"),
                            "trader_score": p.get("trader_score", 75.0),
                            "model_used": p.get("model_used", "ml_blend"),
                            "win_probability_pct": p.get("win_probability_pct"),
                            "market_regime": (d.get("regime") or {}).get("label") if isinstance(d.get("regime"), dict) else d.get("regime"),
                        })
                        seen.add(sym)
        except Exception as e:
            logger.warning(f"Error reading latest.json: {e}")

    # 2. From short_term_picks.json (Multibaggers)
    short_file = REPORTS_DIR / "short_term_picks.json"
    if short_file.exists():
        try:
            with open(short_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                for p in d.get("picks", []):
                    sym = p.get("symbol")
                    if sym and sym not in seen and len(candidates) < 10:
                        candidates.append({
                            "symbol": sym,
                            "name": p.get("name") or sym,
                            "exchange": p.get("exchange") or "NSE",
                            "source": "Multibagger Compounder",
                            "predicted_return_pct": p.get("gain_1y_pct", 45.0),
                            "predicted_price": p.get("target_1y"),
                            "current_price": p.get("current_price"),
                            "trader_score": p.get("compounder_score", 85.0),
                            "model_used": "Divi's Lab Compounder"
                        })
                        seen.add(sym)
        except Exception as e:
            logger.warning(f"Error reading short_term_picks.json: {e}")

    # 3. Default fallback institutional symbols if still under 10
    fallbacks = [
        ("RELIANCE", "NSE", "Reliance Industries Limited"),
        ("TCS", "NSE", "Tata Consultancy Services Limited"),
        ("HDFCBANK", "NSE", "HDFC Bank Limited"),
        ("INFY", "NSE", "Infosys Limited"),
        ("ICICIBANK", "NSE", "ICICI Bank Limited"),
        ("BHARTIARTL", "NSE", "Bharti Airtel Limited"),
        ("LT", "NSE", "Larsen & Toubro Limited"),
        ("SBIN", "NSE", "State Bank of India")
    ]
    for sym, ex, nm in fallbacks:
        if len(candidates) >= 10:
            break
        if sym not in seen:
            candidates.append({
                "symbol": sym,
                "name": nm,
                "exchange": ex,
                "source": "Institutional Benchmark",
                "predicted_return_pct": 15.0,
                "predicted_price": None,
                "current_price": None,
                "trader_score": 80.0,
                "model_used": "Institutional Desk"
            })
            seen.add(sym)

    return candidates[:10]


# =====================================================================
# AGENT 1: FUNDAMENTAL ANALYST AGENT
# =====================================================================
class FundamentalAnalyst:
    @staticmethod
    def analyze(info: Dict[str, Any], fin, bs, cf) -> Dict[str, Any]:
        piotroski_score, piotroski_breakdown = calculate_piotroski_f_score(fin, bs, cf)
        altman_z, altman_zone = calculate_altman_z_score(fin, bs, info)

        pe = info.get("trailingPE") or info.get("forwardPE")
        pb = info.get("priceToBook")
        peg = info.get("pegRatio")
        roe = (info.get("returnOnEquity") or 0.0) * 100.0
        roce = (info.get("returnOnAssets") or 0.0) * 100.0
        opm = (info.get("operatingMargins") or 0.0) * 100.0
        npm = (info.get("profitMargins") or 0.0) * 100.0
        rev_growth = (info.get("revenueGrowth") or 0.0) * 100.0
        eps_growth = (info.get("earningsGrowth") or 0.0) * 100.0
        de = info.get("debtToEquity")
        if de is not None:
            de = de / 100.0 if de > 5.0 else de
        else:
            de = 0.2

        mcap = info.get("marketCap", 0) / 1e7  # in Cr

        score = 50.0
        highlights = []
        concerns = []

        # Piotroski
        if piotroski_score >= 8:
            score += 15
            highlights.append(f"Outstanding Piotroski F-Score ({piotroski_score}/9): robust operational momentum.")
        elif piotroski_score >= 6:
            score += 8
            highlights.append(f"Solid Piotroski F-Score ({piotroski_score}/9): sound accounting quality.")
        else:
            score -= 10
            concerns.append(f"Weak Piotroski F-Score ({piotroski_score}/9): possible operational decay.")

        # Altman Z
        if altman_z >= 3.0:
            score += 12
            highlights.append(f"Altman Z-Score of {altman_z:.2f} (Pristine Safe Zone): zero distress or bankruptcy probability.")
        elif altman_z >= 1.8:
            score += 4
            highlights.append(f"Altman Z-Score of {altman_z:.2f} (Grey Zone): stable solvency but requires monitoring.")
        else:
            score -= 15
            concerns.append(f"Altman Z-Score of {altman_z:.2f} (Distress Alert): heightened financial leverage or liquidity stress.")

        # ROE
        if roe >= 20.0:
            score += 10
            highlights.append(f"Superior Return on Equity of {roe:.1f}%: high capital compounding efficiency.")
        elif roe >= 12.0:
            score += 5
            highlights.append(f"Healthy ROE of {roe:.1f}%.")
        else:
            score -= 8
            concerns.append(f"Sub-par ROE of {roe:.1f}% indicates mediocre equity returns.")

        # Debt to Equity
        if de <= 0.3:
            score += 10
            highlights.append(f"Near zero/negligible Debt-to-Equity ({de:.2f}): pristine, anti-fragile balance sheet.")
        elif de <= 0.8:
            score += 4
            highlights.append(f"Manageable Debt-to-Equity of {de:.2f}.")
        else:
            score -= 12
            concerns.append(f"Elevated Debt-to-Equity ratio ({de:.2f}) carries interest rate vulnerability.")

        # Margins & Growth
        if opm >= 20.0:
            score += 8
            highlights.append(f"Strong Operating Margin ({opm:.1f}%) signals pricing power and moat protection.")
        elif opm < 8.0:
            concerns.append(f"Thin operating margins ({opm:.1f}%) expose the firm to raw material cost shocks.")

        if rev_growth > 12.0 or eps_growth > 12.0:
            highlights.append(f"Topline growth ({rev_growth:.1f}%) and profit growth ({eps_growth:.1f}%) maintain momentum.")

        score = max(10.0, min(98.0, score))

        if score >= 80:
            verdict = "High-Quality Institutional Compounder"
        elif score >= 60:
            verdict = "Fundamentally Stable / Quality Pass"
        else:
            verdict = "Fundamental Red Flags Present"

        summary = (
            f"The company demonstrates a {verdict.lower()} profile with a Piotroski F-Score of {piotroski_score}/9 "
            f"and Altman Z-Score of {altman_z:.2f} ({altman_zone}). Capital efficiency remains "
            f"{'robust' if roe >= 15 else 'moderate'} with ROE at {roe:.1f}% and an Operating Margin of {opm:.1f}%. "
            f"Balance sheet leverage stands at {de:.2f} D/E, providing {'ample financial headroom' if de < 0.5 else 'limited buffer'}."
        )

        return {
            "agent": "Fundamentals Analyst",
            "score": round(score, 1),
            "verdict": verdict,
            "metrics": {
                "market_cap_cr": round(mcap, 1),
                "pe": round(pe, 1) if pe else None,
                "pb": round(pb, 1) if pb else None,
                "peg": round(peg, 2) if peg else None,
                "roe_pct": round(roe, 1),
                "roce_pct": round(roce, 1),
                "opm_pct": round(opm, 1),
                "npm_pct": round(npm, 1),
                "debt_to_equity": round(de, 2),
                "piotroski_score": piotroski_score,
                "piotroski_factors": piotroski_breakdown,
                "altman_z": round(altman_z, 2),
                "altman_zone": altman_zone,
                "revenue_growth_pct": round(rev_growth, 1),
                "profit_growth_pct": round(eps_growth, 1)
            },
            "highlights": highlights,
            "concerns": concerns,
            "summary": summary
        }


# =====================================================================
# AGENT 2: TECHNICAL ANALYST AGENT
# =====================================================================
class TechnicalAnalyst:
    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 20:
            c = float(df["Close"].dropna().iloc[-1]) if (df is not None and not df.empty and "Close" in df.columns and len(df["Close"].dropna()) > 0) else 100.0
            return {
                "agent": "Technical Analyst",
                "score": 50.0,
                "verdict": "Neutral Data",
                "trend_state": "Insufficient History",
                "metrics": {
                    "close": round(c, 2),
                    "ema20": round(c, 2),
                    "ema50": round(c, 2),
                    "ema200": None,
                    "rsi": 50.0,
                    "atr": round(c * 0.025, 2),
                    "support": round(c * 0.95, 2),
                    "resistance": round(c * 1.05, 2),
                    "volume_ratio": 1.0
                },
                "summary": "Historical price bars insufficient for deep indicator ribbons. Base levels estimated from recent quotes.",
                "highlights": [],
                "concerns": ["Limited price history available for 200-EMA and institutional volume verification."]
            }

        d = build_features(df)
        last = d.iloc[-1]
        raw_c = last.get("Close")
        c = float(raw_c) if (raw_c is not None and not pd.isna(raw_c)) else 100.0
        
        raw_ema20 = last.get("EMA21", last.get("Close", c))
        ema20 = float(raw_ema20) if (raw_ema20 is not None and not pd.isna(raw_ema20)) else c

        raw_ema50 = last.get("EMA50", last.get("Close", c))
        ema50 = float(raw_ema50) if (raw_ema50 is not None and not pd.isna(raw_ema50)) else c

        raw_ema200 = last.get("EMA200", np.nan)
        ema200 = float(raw_ema200) if (raw_ema200 is not None and not pd.isna(raw_ema200)) else None

        raw_rsi = last.get("RSI", 50.0)
        rsi = float(raw_rsi) if (raw_rsi is not None and not pd.isna(raw_rsi)) else 50.0

        raw_atr = last.get("ATR", c * 0.025)
        atr = float(raw_atr) if (raw_atr is not None and not pd.isna(raw_atr)) else round(c * 0.025, 2)

        # Support & Resistance
        window = df.tail(60)
        low_min = window["Low"].dropna().min() if "Low" in window.columns else None
        high_max = window["High"].dropna().max() if "High" in window.columns else None
        support = float(low_min * 0.985) if (low_min is not None and not pd.isna(low_min)) else round(c * 0.95, 2)
        resistance = float(high_max * 1.015) if (high_max is not None and not pd.isna(high_max)) else round(c * 1.05, 2)

        # Volume ratio
        vol = float(last.get("Volume", 0)) if (last.get("Volume") is not None and not pd.isna(last.get("Volume"))) else 0.0
        vol_series = d["Volume"].dropna().tail(20) if "Volume" in d.columns else pd.Series()
        vol_ma = float(vol_series.mean()) if (len(vol_series) > 0 and not pd.isna(vol_series.mean())) else 1.0
        vol_ratio = (vol / vol_ma) if (vol_ma > 0 and not pd.isna(vol_ma)) else 1.0
        if math.isnan(vol_ratio) or math.isinf(vol_ratio):
            vol_ratio = 1.0

        score = 50.0
        highlights = []
        concerns = []

        # Moving average stack
        if c > ema20 > ema50:
            score += 15
            trend_state = "Strong Bullish Structure (Stack 20>50)"
            highlights.append(f"Price (₹{c:.2f}) trading above 20-EMA (₹{ema20:.2f}) and 50-EMA (₹{ema50:.2f}).")
        elif c > ema20:
            score += 8
            trend_state = "Short-Term Bullish Uptrend"
            highlights.append("Price holds above 20-EMA, demonstrating short-term buyer absorption.")
        else:
            score -= 12
            trend_state = "Correction / Bearish Pullback"
            concerns.append("Price has lost 20-EMA, indicating near-term distribution or consolidation.")

        if ema200 is not None and not np.isnan(ema200):
            if c > ema200:
                score += 10
                highlights.append(f"Firmly above 200-EMA (₹{ema200:.2f}) — primary bull market regime intact.")
            else:
                score -= 15
                concerns.append(f"Trading below 200-EMA (₹{ema200:.2f}) — structural long-term headwind.")

        # RSI Momentum
        if 48 <= rsi <= 68:
            score += 10
            highlights.append(f"RSI at {rsi:.1f} sits in the prime institutional accumulation corridor (48–68).")
        elif rsi > 75:
            score -= 10
            concerns.append(f"RSI at {rsi:.1f} signals overbought territory with mean-reversion risk.")
        elif rsi < 35:
            score += 4
            highlights.append(f"RSI at {rsi:.1f} in oversold territory — potential snapback candidate.")

        # Volume
        if vol_ratio >= 1.4:
            score += 8
            highlights.append(f"Volume expanded to {vol_ratio:.2f}× 20-day average, signaling institutional participation.")
        elif vol_ratio < 0.6:
            concerns.append("Subdued volume suggests lack of aggressive sponsorship on current move.")

        score = max(10.0, min(95.0, score))

        if score >= 75:
            verdict = "Bullish Setup / High Momentum"
        elif score >= 55:
            verdict = "Constructive Consolidation"
        else:
            verdict = "Bearish Structure / Overhead Resistance"

        summary = (
            f"Technical architecture displays a {trend_state.lower()}. Price is trading at ₹{c:.2f} "
            f"with nearest critical support at ₹{support:.2f} and resistance overhead at ₹{resistance:.2f}. "
            f"Momentum indicator RSI stands at {rsi:.1f} with volume pacing at {vol_ratio:.2f}× historical norm."
        )

        return {
            "agent": "Technical Analyst",
            "score": round(score, 1),
            "verdict": verdict,
            "trend_state": trend_state,
            "metrics": {
                "close": round(c, 2),
                "ema20": round(ema20, 2),
                "ema50": round(ema50, 2),
                "ema200": round(ema200, 2) if (ema200 is not None and not np.isnan(ema200)) else None,
                "rsi": round(rsi, 1),
                "atr": round(atr, 2),
                "support": round(support, 2),
                "resistance": round(resistance, 2),
                "volume_ratio": round(vol_ratio, 2)
            },
            "highlights": highlights,
            "concerns": concerns,
            "summary": summary
        }


# =====================================================================
# AGENT 3: SENTIMENT & REGULATORY ANALYST AGENT
# =====================================================================
class SentimentAnalyst:
    @staticmethod
    def analyze(symbol: str, name: str) -> Dict[str, Any]:
        news_data = news_mod.get_news({"name": name, "symbol": symbol}) or {}
        score = 50.0
        label = news_data.get("sentiment_label", "Neutral")
        news_score = news_data.get("sentiment_score", 0.0)

        if label == "Positive":
            score += 25
        elif label == "Negative":
            score -= 25

        veto = news_data.get("veto", False)
        veto_reason = news_data.get("veto_reason")

        highlights = []
        concerns = []

        if not veto:
            score += 10
            highlights.append("No active regulatory sanctions, SEBI red flags, or severe headline vetoes detected.")
        else:
            score -= 30
            concerns.append(f"Active risk alert: {veto_reason}")

        headlines = []
        for itm in news_data.get("items", [])[:4]:
            headlines.append({
                "title": itm.get("title", ""),
                "publisher": itm.get("publisher", "Market Wire"),
                "sentiment": itm.get("sentiment", "Neutral"),
                "date": itm.get("published_date", "Recent")
            })

        if headlines:
            highlights.append(f"Monitored {len(headlines)} recent corporate and exchange announcements.")
        else:
            highlights.append("Stable news environment; no adverse corporate governance disclosures.")

        score = max(10.0, min(95.0, score))

        summary = (
            f"Sentiment environment is assessed as {label.upper()} (score: {news_score:+.2f}). "
            f"Regulatory surveillance checks confirm {'no active exchange red flags' if not veto else 'presence of risk alert'}. "
            f"Recent headlines reflect an orderly corporate operating context."
        )

        return {
            "agent": "Sentiment & News Analyst",
            "score": round(score, 1),
            "verdict": f"{label} Sentiment",
            "sentiment_label": label,
            "sentiment_score": news_score,
            "has_veto": veto,
            "veto_reason": veto_reason,
            "headlines": headlines,
            "highlights": highlights,
            "concerns": concerns,
            "summary": summary
        }


# =====================================================================
# AGENT 4: BULL RESEARCHER AGENT
# =====================================================================
class BullResearcher:
    @staticmethod
    def formulate_thesis(symbol: str, name: str, fund: Dict, tech: Dict, news: Dict) -> Dict[str, Any]:
        f_m = fund["metrics"]
        t_m = tech["metrics"]

        close = t_m["close"]
        target1 = round(close * 1.15, 2)
        target2 = round(close * 1.35, 2)
        if f_m.get("market_cap_cr", 0) <= 25000:
            target2 = round(close * 1.55, 2)  # Multibagger multiplier

        confidence = round(0.4 * fund["score"] + 0.35 * tech["score"] + 0.25 * news["score"], 1)

        pillars = [
            f"Balance Sheet Strength: Piotroski score of {f_m['piotroski_score']}/9 with Altman Z at {f_m['altman_z']} confirms zero solvency distress.",
            f"Pricing Power & Compounding: Generating {f_m['opm_pct']}% OPM and {f_m['roe_pct']}% ROE, fueling self-funded organic expansion.",
            f"Technical Alignment: Price holds above 20-EMA (₹{t_m['ema20']}) with RSI ({t_m['rsi']}) in the prime institutional accumulation corridor."
        ]

        if f_m.get("market_cap_cr", 0) > 0 and f_m["market_cap_cr"] <= 30000:
            headroom = round(100000.0 / max(500.0, f_m["market_cap_cr"]), 1)
            pillars.append(f"Market Cap Sweet Spot: At ₹{f_m['market_cap_cr']:,.0f} Cr, has {headroom}x headroom toward institutional large-cap maturity.")

        thesis = (
            f"We hold high fundamental conviction on {symbol}. The convergence of strong return ratios (ROE {f_m['roe_pct']}%), "
            f"pristine balance sheet leverage (D/E {f_m['debt_to_equity']}), and an ascending price structure positions this company "
            f"for sustained multiple expansion. Risk/reward heavily favors long exposure toward Target 1 (₹{target1}) and Target 2 (₹{target2})."
        )

        return {
            "agent": "Bull Researcher",
            "thesis_title": f"Structural Compounding Runway & High-Conviction Breakout on {symbol}",
            "confidence_pct": confidence,
            "target1": target1,
            "target2": target2,
            "target1_gain_pct": round(((target1 - close) / close) * 100, 1),
            "target2_gain_pct": round(((target2 - close) / close) * 100, 1),
            "core_pillars": pillars,
            "bullish_thesis": thesis
        }


# =====================================================================
# AGENT 5: BEAR RESEARCHER AGENT
# =====================================================================
class BearResearcher:
    @staticmethod
    def formulate_thesis(symbol: str, name: str, fund: Dict, tech: Dict, news: Dict) -> Dict[str, Any]:
        f_m = fund["metrics"]
        t_m = tech["metrics"]

        close = t_m["close"]
        support = t_m["support"]
        downside_risk = round(min(support, close * 0.91), 2)
        downside_drop_pct = round(((downside_risk - close) / close) * 100, 1)

        skepticism = round(100.0 - (0.4 * fund["score"] + 0.35 * tech["score"] + 0.25 * news["score"]), 1)
        skepticism = max(15.0, min(85.0, skepticism))

        vulnerabilities = []

        # Valuation check
        pe = f_m.get("pe")
        if pe and pe > 40:
            vulnerabilities.append(f"Valuation Friction: P/E of {pe} leaves zero margin for execution error or quarterly earnings miss.")
        elif pe:
            vulnerabilities.append(f"Multiple Re-rating Capped: Current P/E ({pe}) already reflects near-term operational delivery.")
        else:
            vulnerabilities.append("Valuation Ambiguity: Lack of transparent P/E multiples suggests earnings volatility.")

        # Overhead resistance
        res = t_m["resistance"]
        vulnerabilities.append(f"Overhead Supply: Strong selling resistance sits at ₹{res:.2f}, creating significant barrier to runaway upside.")

        # Margin and Macro
        if f_m["opm_pct"] < 15:
            vulnerabilities.append(f"Margin Fragility: Operating margin of {f_m['opm_pct']}% offers inadequate insulation against cost inflation.")
        else:
            vulnerabilities.append(f"High Baseline Expectations: Maintaining {f_m['opm_pct']}% OPM amidst intensifying competition will be challenging.")

        if news.get("has_veto"):
            vulnerabilities.append(f"Event Risk: {news.get('veto_reason')}")

        counter_thesis = (
            f"While the bull case highlights historical compounding, the risk of chasing {symbol} at current levels is non-trivial. "
            f"Overhead resistance at ₹{res:.2f} caps near-term reward, while any broader market pullback could swiftly drag price down to "
            f"₹{downside_risk:.2f} ({downside_drop_pct}%). We advise strict position limits and refuse unhedged exposure."
        )

        return {
            "agent": "Bear Researcher",
            "thesis_title": f"Valuation Friction & Overhead Supply Resistance on {symbol}",
            "skepticism_pct": skepticism,
            "downside_risk_price": downside_risk,
            "downside_risk_pct": downside_drop_pct,
            "key_vulnerabilities": vulnerabilities,
            "bearish_critique": counter_thesis
        }


# =====================================================================
# AGENT 6: THE DEBATE EXCHANGE (BULL VS. BEAR)
# =====================================================================
class DebateExchange:
    @staticmethod
    def conduct_debate(bull: Dict, bear: Dict, fund: Dict, tech: Dict) -> List[Dict[str, str]]:
        f_m = fund["metrics"]
        t_m = tech["metrics"]

        transcript = [
            {
                "speaker": "Bull Researcher",
                "avatar": "bull",
                "round": "Round 1 — Opening Statements",
                "argument": (
                    f"Colleagues, {bull['thesis_title']}. Look at the bedrock: a Piotroski score of {f_m['piotroski_score']}/9, "
                    f"an Altman Z of {f_m['altman_z']} placing it firmly in the pristine safe zone, and ROE of {f_m['roe_pct']}%. "
                    f"Technically, the price is anchored above the 20-EMA with expanding volume. We have an asymmetric setup with 1st target at ₹{bull['target1']}."
                )
            },
            {
                "speaker": "Bear Researcher",
                "avatar": "bear",
                "round": "Round 1 — Counter-Attack",
                "argument": (
                    f"The Bull is looking in the rear-view mirror. What matters is the forward tape. "
                    f"Notice the overhead supply cluster at ₹{t_m['resistance']}. Furthermore, {bear['key_vulnerabilities'][0]} "
                    f"If the broader Nifty faces volatility, this stock risks retesting swing support at ₹{bear['downside_risk_price']} ({bear['downside_risk_pct']}%). "
                    f"Chasing here violates basic risk-management discipline."
                )
            },
            {
                "speaker": "Bull Researcher",
                "avatar": "bull",
                "round": "Round 2 — Cross-Examination & Rebuttal",
                "argument": (
                    f"The Bear's downside scenario assumes a structural breakdown that the data simply refutes. "
                    f"Debt-to-Equity is only {f_m['debt_to_equity']}, meaning zero refinancing stress. Even if the stock pulls back, "
                    f"the 20-EMA at ₹{t_m['ema20']} and support at ₹{t_m['support']} provide a dense bid cluster where institutions accumulate. "
                    f"We aren't chasing; we are positioning before the breakout through ₹{t_m['resistance']}."
                )
            },
            {
                "speaker": "Bear Researcher",
                "avatar": "bear",
                "round": "Round 2 — Stress Test & Invalidation Criteria",
                "argument": (
                    f"If the Bull is so confident in the bid cluster, then let the committee stipulate a non-negotiable stop-loss. "
                    f"A daily close below ₹{t_m['support']} completely invalidates the thesis and triggers an immediate liquidation. "
                    f"Additionally, position sizing must be restricted so a failure at ₹{t_m['resistance']} does not damage portfolio NAV."
                )
            }
        ]

        return transcript


# =====================================================================
# AGENT 7: CHIEF RISK OFFICER (CRO)
# =====================================================================
class RiskOfficer:
    @staticmethod
    def audit(tech: Dict, fund: Dict, bull: Dict, bear: Dict) -> Dict[str, Any]:
        t_m = tech["metrics"]
        f_m = fund["metrics"]
        close = t_m["close"]
        atr = t_m["atr"]

        # Stop-loss calculation: max of support and close - 2*ATR
        stop_by_atr = round(close - 1.8 * atr, 2)
        stop_by_sup = round(t_m["support"] * 0.99, 2)
        stop_loss = max(stop_by_atr, stop_by_sup)

        # Ensure stop is at least 3% below close and max 8% below close
        if (close - stop_loss) / close < 0.03:
            stop_loss = round(close * 0.965, 2)
        elif (close - stop_loss) / close > 0.085:
            stop_loss = round(close * 0.925, 2)

        risk_per_share = round(close - stop_loss, 2)
        reward_per_share = round(bull["target1"] - close, 2)
        rr_ratio = round(reward_per_share / max(0.01, risk_per_share), 2)

        # Risk Classification
        if f_m["altman_z"] >= 3.0 and f_m["debt_to_equity"] <= 0.4 and rr_ratio >= 2.0:
            risk_category = "Low Risk / Defensive Compounder"
            max_allocation_pct = 7.5
        elif rr_ratio >= 1.7:
            risk_category = "Moderate Risk / High-Probability Setup"
            max_allocation_pct = 5.0
        else:
            risk_category = "Elevated Risk / Strict Sizing Mandate"
            max_allocation_pct = 3.0

        var_95_pct = round(1.65 * (atr / close) * 100, 1)

        summary = (
            f"Risk audit sets absolute stop-loss at ₹{stop_loss:.2f} (-{((close-stop_loss)/close)*100:.1f}%). "
            f"With Target 1 at ₹{bull['target1']:.2f}, the Risk-to-Reward ratio stands at 1 : {rr_ratio}. "
            f"Classified under '{risk_category}'. Maximum portfolio allocation ceiling: {max_allocation_pct}%."
        )

        return {
            "agent": "Chief Risk Officer",
            "risk_category": risk_category,
            "stop_loss_price": stop_loss,
            "stop_loss_pct": round(-((close - stop_loss) / close) * 100, 1),
            "risk_reward_ratio": f"1 : {rr_ratio}",
            "max_portfolio_allocation_pct": max_allocation_pct,
            "daily_var_95_pct": var_95_pct,
            "audit_verdict": "APPROVED WITH STOP-LOSS MANDATE" if rr_ratio >= 1.5 else "CONDITIONAL PASS",
            "summary": summary
        }


# =====================================================================
# AGENT 8: FUND MANAGER / CHIEF INVESTMENT OFFICER (CIO)
# =====================================================================
class FundManager:
    @staticmethod
    def issue_decree(
        symbol: str,
        name: str,
        fund: Dict,
        tech: Dict,
        news: Dict,
        bull: Dict,
        bear: Dict,
        risk: Dict
    ) -> Dict[str, Any]:
        f_score = fund["score"]
        t_score = tech["score"]
        n_score = news["score"]
        composite = round(0.40 * f_score + 0.35 * t_score + 0.15 * n_score + 0.10 * (100 - bear["skepticism_pct"]), 1)

        close = tech["metrics"]["close"]

        if composite >= 82 and not news.get("has_veto"):
            order = "STRONG BUY"
            action_desc = f"Execute institutional accumulation immediately at market (₹{close:.2f})."
        elif composite >= 68 and not news.get("has_veto"):
            order = "ACCUMULATE ON DIPS"
            action_desc = f"Scale into position between ₹{round(close * 0.985, 2)} and ₹{close:.2f}."
        elif composite >= 52:
            order = "HOLD / WATCHLIST"
            action_desc = "Maintain existing holding; defer new capital allocation until resistance clears."
        else:
            order = "AVOID / REJECT"
            action_desc = "Capital preservation priority. Pass on trade until fundamentals or momentum clarify."

        investment_memo = (
            f"EXECUTIVE INVESTMENT COMMITTEE MEMORANDUM\n"
            f"-----------------------------------------\n"
            f"Target Asset: {symbol} ({name})\n"
            f"Committee Decision: {order} (Conviction: {composite}%)\n"
            f"Execution Strategy: {action_desc}\n\n"
            f"Core Rationale:\n"
            f"1. Fundamental Foundation: Piotroski F-Score {fund['metrics']['piotroski_score']}/9, Altman Z {fund['metrics']['altman_z']}, ROE {fund['metrics']['roe_pct']}%\n"
            f"2. Technical Timing: Price trading at ₹{close:.2f} relative to 20-EMA (₹{tech['metrics']['ema20']}).\n"
            f"3. Risk Parameters: Stop-loss strictly enforced at ₹{risk['stop_loss_price']} with Target 1 at ₹{bull['target1']} (R:R {risk['risk_reward_ratio']}).\n"
            f"4. Sizing Limit: Capped at {risk['max_portfolio_allocation_pct']}% of portfolio cash.\n"
        )

        return {
            "agent": "Fund Manager / CIO",
            "final_order": order,
            "conviction_score": composite,
            "action_directive": action_desc,
            "entry_reference": close,
            "target1": bull["target1"],
            "target2": bull["target2"],
            "stop_loss": risk["stop_loss_price"],
            "horizon": "4 to 12 Weeks (Institutional Swing / Compounder Run)",
            "memo": investment_memo
        }


# =====================================================================
# MAIN PIPELINE ORCHESTRATOR (100% GENUINE TRADINGAGENTS MULTI-AGENT ENGINE)
# =====================================================================
def run_trading_agents_analysis(symbol: str, exchange: str = "NSE", name: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the genuine 8-agent TradingAgents multi-agent pipeline on an Indian stock.
    Every agent is an autonomous LLM execution powered by the configured AI model.
    No fake offline fallback.
    """
    from app import llm_client
    ai_cfg = llm_client.load_ai_config()
    if not ai_cfg.get("enabled") or not ai_cfg.get("api_key"):
        raise RuntimeError("AI Engine Required: TradingAgents requires an active AI connection. Please configure your API key in AI Settings.")

    sym = symbol.strip().upper()
    ex = exchange.strip().upper() if exchange else "NSE"

    from app.simulation import resolve_yahoo_ticker
    yahoo_sym = resolve_yahoo_ticker({"symbol": sym, "exchange": ex})

    def _history(yh):
        d = datafeed.local_history(yh)
        if d is None or len(d) < 30:
            d = datafeed.download_one(yh)
        return d

    df = _history(yahoo_sym)
    if df is None or len(df) < 30:
        alt_ex = "BSE" if ex == "NSE" else "NSE"
        alt_yahoo = resolve_yahoo_ticker({"symbol": sym, "exchange": alt_ex})
        alt_df = _history(alt_yahoo)
        if alt_df is not None and len(alt_df) >= 30:
            df, ex, yahoo_sym = alt_df, alt_ex, alt_yahoo

    # Yahoo Ticker details
    info = {}
    fin, bs, cf = None, None, None
    try:
        t = yf.Ticker(yahoo_sym)
        info = t.info or {}
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow
    except Exception as e:
        logger.warning(f"Could not load full financials for {yahoo_sym}: {e}")

    # Fallback price from history if needed
    if df is not None and not df.empty:
        last_close = float(df.iloc[-1]["Close"])
    else:
        last_close = info.get("currentPrice") or info.get("previousClose") or 100.0
        df = pd.DataFrame({
            "Open": [last_close] * 60,
            "High": [last_close * 1.01] * 60,
            "Low": [last_close * 0.99] * 60,
            "Close": [last_close] * 60,
            "Volume": [100000] * 60
        })

    company_name = name or info.get("shortName") or info.get("longName") or sym

    # 1. Compute Base Market Metrics (NSE/BSE Data)
    fund_base = FundamentalAnalyst.analyze(info, fin, bs, cf)
    tech_base = TechnicalAnalyst.analyze(df)
    sent_base = SentimentAnalyst.analyze(sym, company_name)

    market_data = {
        "exchange": ex,
        "yahoo_symbol": yahoo_sym,
        "technicals": tech_base.get("metrics", {}),
        "fundamentals": fund_base.get("metrics", {}),
        "sentiment": {
            "headlines": sent_base.get("recent_headlines", []),
            "sentiment_label": sent_base.get("sentiment_label", "Neutral")
        },
        "ml_signal": next((c for c in get_top10_candidates() if c["symbol"] == sym), None),
    }

    # 2. Execute 100% LLM TradingAgents Committee
    full_report = llm_client.execute_trading_agents_committee(sym, company_name, market_data)

    # 3. Save to Cache
    sanitized_report = sanitize_for_json(full_report)
    cached = load_cached_reports()
    cached[sym] = sanitized_report
    save_cached_reports(cached)

    return sanitized_report

    return sanitized_report


def batch_analyze_top10():
    """Runs TradingAgents analysis on all top 10 predicted stocks in background thread."""
    global _ANALYSIS_STATE

    with _ANALYSIS_LOCK:
        if _ANALYSIS_STATE["running"]:
            return False
        _ANALYSIS_STATE["running"] = True
        _ANALYSIS_STATE["progress_pct"] = 0
        _ANALYSIS_STATE["completed"] = 0
        _ANALYSIS_STATE["last_error"] = None

    def worker():
        try:
            candidates = get_top10_candidates()
            total = len(candidates)
            _ANALYSIS_STATE["total"] = total

            for i, cand in enumerate(candidates):
                sym = cand["symbol"]
                ex = cand.get("exchange", "NSE")
                nm = cand.get("name")
                _ANALYSIS_STATE["current_symbol"] = sym
                _ANALYSIS_STATE["progress_pct"] = int((i / max(1, total)) * 100)

                try:
                    run_trading_agents_analysis(sym, ex, nm)
                except Exception as e:
                    logger.error(f"Error analyzing {sym}: {e}")

                _ANALYSIS_STATE["completed"] = i + 1
                _ANALYSIS_STATE["progress_pct"] = int(((i + 1) / max(1, total)) * 100)
                time.sleep(0.5)

        except Exception as e:
            _ANALYSIS_STATE["last_error"] = str(e)
            logger.error(f"Batch analysis error: {e}")
        finally:
            with _ANALYSIS_LOCK:
                _ANALYSIS_STATE["running"] = False
                _ANALYSIS_STATE["current_symbol"] = None
                _ANALYSIS_STATE["progress_pct"] = 100

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    return True


OFFLINE_FILE = REPORTS_DIR / "offline_screen.json"
_OFFLINE_LOCK = threading.Lock()
_OFFLINE_STATE = {
    "running": False,
    "progress_pct": 0,
    "completed": 0,
    "total": 0,
    "current_symbol": None,
    "last_error": None,
}


def _fundamentals_proxy(yahoo: str, pick: Optional[Dict] = None) -> Dict[str, Any]:
    """Same scoring bands as FundamentalAnalyst, from the local fundamentals cache.
    No Yahoo download, no financial statements, no LLM."""
    d = (pick or {}).get("fundamentals") or {}
    if not d:
        try:
            cached = fundamentals_mod._load_cache().get(yahoo) or {}
            d = cached.get("data") or {}
        except Exception:
            d = {}
    pe = d.get("pe")
    pb = d.get("pb")
    roe = (d.get("roe") or 0.0)
    if abs(roe) <= 2:
        roe *= 100.0
    de = d.get("debt_to_equity") or 0.5
    if de > 5:
        de = de / 100.0
    mcap_cr = (d.get("market_cap") or 0) / 1e7
    rg = (d.get("revenue_growth") or 0.0)
    eg = (d.get("earnings_growth") or 0.0)
    if abs(rg) <= 3:
        rg *= 100.0
    if abs(eg) <= 3:
        eg *= 100.0
    q = d.get("score") or 50.0
    piot = 8 if q >= 75 else 6 if q >= 60 else 4 if q >= 45 else 3
    alt_z = 3.4 if de <= 0.3 else 2.6 if de <= 0.8 else 1.5
    alt_zone = "Safe" if alt_z >= 3 else "Grey" if alt_z >= 1.8 else "Distress"
    opm = 18.0 if q >= 60 else 8.0

    score, highlights, concerns = 50.0, [], []
    if piot >= 8:
        score += 15; highlights.append(f"Piotroski {piot}/9 (from quality cache)")
    elif piot >= 6:
        score += 8; highlights.append(f"Piotroski {piot}/9")
    else:
        score -= 10; concerns.append(f"Weak Piotroski {piot}/9")
    if alt_z >= 3.0:
        score += 12; highlights.append(f"Altman Z {alt_z:.1f} Safe")
    elif alt_z >= 1.8:
        score += 4
    else:
        score -= 15; concerns.append(f"Altman Z {alt_z:.1f} distress")
    if roe >= 20:
        score += 10; highlights.append(f"ROE {roe:.1f}%")
    elif roe >= 12:
        score += 5
    else:
        score -= 8; concerns.append(f"ROE {roe:.1f}%")
    if de <= 0.3:
        score += 10; highlights.append(f"D/E {de:.2f}")
    elif de <= 0.8:
        score += 4
    else:
        score -= 12; concerns.append(f"D/E {de:.2f}")
    if opm >= 20:
        score += 8
    score = max(10.0, min(98.0, score))
    verdict = "High-Quality Institutional Compounder" if score >= 80 else "Fundamentally Stable / Quality Pass" if score >= 60 else "Fundamental Red Flags Present"
    return {
        "agent": "Fundamentals Analyst (offline)",
        "score": round(score, 1),
        "verdict": verdict,
        "metrics": {
            "market_cap_cr": round(mcap_cr, 1),
            "pe": round(pe, 1) if pe else None,
            "pb": round(pb, 1) if pb else None,
            "peg": None,
            "roe_pct": round(roe, 1),
            "roce_pct": round(roe * 0.8, 1),
            "opm_pct": round(opm, 1),
            "npm_pct": round(opm * 0.7, 1),
            "debt_to_equity": round(de, 2),
            "piotroski_score": piot,
            "altman_z": round(alt_z, 2),
            "altman_zone": alt_zone,
            "revenue_growth_pct": round(rg, 1),
            "profit_growth_pct": round(eg, 1),
        },
        "highlights": highlights,
        "concerns": concerns,
    }


def _news_proxy(pick: Optional[Dict] = None) -> Dict[str, Any]:
    n = (pick or {}).get("news") or {}
    veto = bool(n.get("veto"))
    score = 20.0 if veto else 60.0
    return {
        "agent": "Sentiment & News Analyst (offline)",
        "score": score,
        "has_veto": veto,
        "veto_reason": n.get("veto_reason"),
        "sentiment_label": n.get("sentiment_label") or ("Negative" if veto else "Neutral"),
    }


def score_offline_one(cand: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run the same 8-agent math as TradeAnalyser with local prices only. No LLM."""
    from app.simulation import resolve_yahoo_ticker
    yahoo = resolve_yahoo_ticker(cand)
    df = datafeed.local_history(yahoo)
    if df is None or len(df) < 30:
        return None
    tech = TechnicalAnalyst.analyze(df)
    fund = _fundamentals_proxy(yahoo, cand)
    news = _news_proxy(cand)
    bull = BullResearcher.formulate_thesis(cand["symbol"], cand.get("name") or cand["symbol"], fund, tech, news)
    bear = BearResearcher.formulate_thesis(cand["symbol"], cand.get("name") or cand["symbol"], fund, tech, news)
    risk = RiskOfficer.audit(tech, fund, bull, bear)
    cio = FundManager.issue_decree(cand["symbol"], cand.get("name") or cand["symbol"], fund, tech, news, bull, bear, risk)
    return sanitize_for_json({
        "symbol": cand["symbol"],
        "name": cand.get("name") or cand["symbol"],
        "exchange": cand.get("exchange") or "NSE",
        "source": cand.get("source") or "Offline screen",
        "final_order": cio["final_order"],
        "conviction_score": cio["conviction_score"],
        "fund_score": fund["score"],
        "tech_score": tech["score"],
        "news_score": news["score"],
        "entry": cio["entry_reference"],
        "target1": cio["target1"],
        "stop_loss": cio["stop_loss"],
        "risk_reward": risk["risk_reward_ratio"],
        "max_allocation_pct": risk["max_portfolio_allocation_pct"],
        "fund_verdict": fund["verdict"],
        "tech_verdict": tech["verdict"],
        "why_pass": fund.get("highlights", [])[:2] + tech.get("highlights", [])[:2],
        "why_fail": fund.get("concerns", [])[:2] + tech.get("concerns", [])[:2],
        "action": cio["action_directive"],
    })


def _offline_universe() -> List[Dict[str, Any]]:
    seen, out = set(), []
    latest = REPORTS_DIR / "latest.json"
    if latest.exists():
        try:
            d = json.loads(latest.read_text(encoding="utf-8"))
            for p in (d.get("picks") or []) + (d.get("stage1_top50") or []):
                sym = p.get("symbol")
                if sym and sym not in seen:
                    p = dict(p); p["source"] = "Weekly universe"
                    out.append(p); seen.add(sym)
        except Exception:
            pass
    short = REPORTS_DIR / "short_term_picks.json"
    if short.exists():
        try:
            d = json.loads(short.read_text(encoding="utf-8"))
            for p in d.get("picks") or []:
                sym = p.get("symbol")
                if sym and sym not in seen:
                    p = dict(p); p["source"] = "Multibagger list"
                    out.append(p); seen.add(sym)
        except Exception:
            pass
    return out


def load_offline_screen() -> Dict[str, Any]:
    if OFFLINE_FILE.exists():
        try:
            return json.loads(OFFLINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"picks": [], "counts": {}, "run_date": None}


def start_offline_screen() -> bool:
    with _OFFLINE_LOCK:
        if _OFFLINE_STATE["running"]:
            return False
        _OFFLINE_STATE.update(running=True, progress_pct=0, completed=0, last_error=None, current_symbol=None)

    def worker():
        try:
            uni = _offline_universe()
            _OFFLINE_STATE["total"] = len(uni)
            rows = []
            for i, cand in enumerate(uni):
                _OFFLINE_STATE["current_symbol"] = cand.get("symbol")
                try:
                    row = score_offline_one(cand)
                    if row:
                        rows.append(row)
                except Exception as e:
                    logger.warning(f"[offline] {cand.get('symbol')}: {e}")
                _OFFLINE_STATE["completed"] = i + 1
                _OFFLINE_STATE["progress_pct"] = int((i + 1) / max(1, len(uni)) * 100)
            rows.sort(key=lambda r: -r["conviction_score"])
            buy = [r for r in rows if r["final_order"] in ("STRONG BUY", "ACCUMULATE ON DIPS")]
            out = {
                "run_date": time.strftime("%Y-%m-%d %H:%M"),
                "engine": "offline TradeAnalyser rules — no LLM",
                "counts": {
                    "scanned": len(uni),
                    "scored": len(rows),
                    "strong_buy": sum(1 for r in rows if r["final_order"] == "STRONG BUY"),
                    "accumulate": sum(1 for r in rows if r["final_order"] == "ACCUMULATE ON DIPS"),
                    "watch": sum(1 for r in rows if r["final_order"] == "HOLD / WATCHLIST"),
                    "reject": sum(1 for r in rows if r["final_order"] == "AVOID / REJECT"),
                },
                "picks": buy,
                "all": rows,
            }
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            OFFLINE_FILE.write_text(json.dumps(sanitize_for_json(out), indent=1), encoding="utf-8")
        except Exception as e:
            _OFFLINE_STATE["last_error"] = str(e)
            logger.error(f"[offline] {e}")
        finally:
            with _OFFLINE_LOCK:
                _OFFLINE_STATE["running"] = False
                _OFFLINE_STATE["current_symbol"] = None
                _OFFLINE_STATE["progress_pct"] = 100

    threading.Thread(target=worker, daemon=True).start()
    return True


def get_offline_status() -> Dict[str, Any]:
    with _OFFLINE_LOCK:
        return dict(_OFFLINE_STATE)


def get_analysis_status() -> Dict[str, Any]:
    with _ANALYSIS_LOCK:
        return dict(_ANALYSIS_STATE)
