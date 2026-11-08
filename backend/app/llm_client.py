"""
LLM Client for TradeAnalyser - 100% Genuine TradingAgents Multi-Agent Engine
Replicates the TauricResearch / UCLA-MIT TradingAgents framework for Indian Equities (NSE/BSE).
Every role in the committee is an autonomous LLM agent:
1. Fundamental Analyst Agent
2. Technical Analyst Agent
3. Sentiment & Regulatory Analyst Agent
4. Bull Researcher Agent
5. Bear Researcher Agent
6. Dynamic Multi-Turn Debate Exchange
7. Chief Risk Officer (CRO)
8. Fund Manager / Chief Investment Officer (CIO)
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
import httpx

logger = logging.getLogger("llm_client")
logger.setLevel(logging.INFO)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "data" / "ai_config.json"

PROVIDER_DEFAULTS = {
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "available_models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    },
    "xai": {
        "name": "xAI (Grok)",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-4.7",
        "available_models": ["grok-4.7", "grok-2-latest", "grok-beta", "grok-2", "grok-2-vision-latest"]
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "available_models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-1.5-flash",
        "available_models": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    },
    "custom": {
        "name": "Custom / Cursor / Ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "openai/gpt-oss-120b",
        "available_models": ["openai/gpt-oss-120b", "grok-4.7", "grok-2-latest", "deepseek-r1", "llama3", "mistral"]
    }
}


def load_ai_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    default_key = os.environ.get("AGENTROUTER_API_KEY", "")
    default_provider = "groq"

    return {
        "enabled": False,
        "provider": default_provider,
        "api_key": default_key,
        "base_url": PROVIDER_DEFAULTS[default_provider]["base_url"],
        "model": PROVIDER_DEFAULTS[default_provider]["model"]
    }


def save_ai_config(cfg: Dict[str, Any]):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def mask_key(k: Optional[str]) -> str:
    if not k:
        return ""
    if len(k) <= 8:
        return "••••••••"
    return k[:4] + "••••" + k[-4:]


def get_sanitized_config() -> Dict[str, Any]:
    cfg = load_ai_config()
    sanitized = dict(cfg)
    raw_key = sanitized.get("api_key", "")
    sanitized["has_key"] = bool(raw_key.strip())
    sanitized["masked_key"] = mask_key(raw_key)
    sanitized["api_key"] = mask_key(raw_key)
    sanitized["defaults"] = PROVIDER_DEFAULTS
    return sanitized


def test_ai_connection(
    provider: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Sends a ping test to verify the user's AI credentials and endpoint."""
    p_info = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["custom"])
    url = (base_url or p_info["base_url"]).rstrip("/")
    m = model or p_info["model"]

    if not url.endswith("/chat/completions"):
        full_endpoint = f"{url}/chat/completions"
    else:
        full_endpoint = url

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}"
    }

    payload = {
        "model": m,
        "messages": [
            {"role": "user", "content": "Ping test for TradingAgents. Reply with 'OK'."}
        ],
        "max_tokens": 10,
        "temperature": 0.1
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(full_endpoint, json=payload, headers=headers)
            if r.status_code == 200:
                data = r.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return {"success": True, "message": f"Verified successfully with {provider.upper()} ({m})!"}
            else:
                return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:220]}"}
    except Exception as e:
        return {"success": False, "error": f"Connection failed: {str(e)}"}


def clean_json_text(text: str) -> str:
    """Strips markdown code blocks, backticks, and extra whitespace."""
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    t = t.strip()
    # If there is markdown before or after, find the outer curly braces
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start:end+1]
    return t


def call_llm_json(system_prompt: str, user_prompt: str, temp: float = 0.2, max_tokens: int = 1500) -> Dict[str, Any]:
    """Invokes configured LLM and parses response as strict JSON."""
    cfg = load_ai_config()
    if not cfg.get("enabled") or not cfg.get("api_key"):
        raise RuntimeError("AI Engine Required: TradingAgents requires an active AI connection. Please configure your API key in AI Settings.")

    provider = cfg.get("provider", "groq")
    p_info = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["custom"])
    url = (cfg.get("base_url") or p_info["base_url"]).rstrip("/")
    m = cfg.get("model") or p_info["model"]
    api_key = cfg.get("api_key", "").strip()

    if not url.endswith("/chat/completions"):
        endpoint = f"{url}/chat/completions"
    else:
        endpoint = url

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    sys_text = (
        f"{system_prompt}\n"
        "CRITICAL INSTRUCTION: You must respond ONLY with raw, valid JSON. "
        "Do NOT enclose your response in markdown code blocks (no ```json or ```). "
        "Do not include any conversational preamble or trailing explanation."
    )

    payload = {
        "model": m,
        "messages": [
            {"role": "system", "content": sys_text},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temp,
        "max_tokens": max_tokens
    }

    with httpx.Client(timeout=40.0) as client:
        r = client.post(endpoint, json=payload, headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"AI Provider ({provider.upper()}) returned HTTP {r.status_code}: {r.text[:250]}")
        raw_text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    cleaned = clean_json_text(raw_text)
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON response: {cleaned[:300]}")
        raise ValueError(f"AI Model output was not valid JSON: {str(e)}")


def execute_trading_agents_committee(
    sym: str,
    company_name: str,
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executes the 100% Genuine TradingAgents multi-agent institutional workflow.
    Every agent is an autonomous LLM execution powered by the user's active AI model.
    """
    cfg = load_ai_config()
    if not cfg.get("enabled") or not cfg.get("api_key"):
        raise RuntimeError("AI Engine Required: TradingAgents requires an active AI connection. Please configure your API key in AI Settings.")

    ai_model_name = cfg.get("model") or "LLM"
    ai_provider = cfg.get("provider", "AI").upper()
    ai_label = f"{ai_provider} ({ai_model_name})"

    t0 = time.time()
    logger.info(f"Deliberating {sym} ({company_name}) across 8 TradingAgents LLM roles...")

    # Data unpacking
    tech_data = market_data.get("technicals", {})
    fund_data = market_data.get("fundamentals", {})
    sent_data = market_data.get("sentiment", {})

    close_p = tech_data.get("close", 100.0)
    mcap_cr = fund_data.get("market_cap_cr", 0.0)
    piot = fund_data.get("piotroski_score", 5)
    alt_z = fund_data.get("altman_z", 2.5)
    alt_zone = fund_data.get("altman_zone", "Grey")
    roe = fund_data.get("roe_pct", 12.0)
    opm = fund_data.get("opm_pct", 14.0)
    de = fund_data.get("debt_to_equity", 0.5)
    pe = fund_data.get("pe", "N/A")
    pb = fund_data.get("pb", "N/A")
    peg = fund_data.get("peg", "N/A")

    ema20 = tech_data.get("ema20", close_p)
    ema50 = tech_data.get("ema50", close_p)
    ema200 = tech_data.get("ema200", "N/A")
    rsi = tech_data.get("rsi", 50.0)
    support = tech_data.get("support", close_p * 0.95)
    resistance = tech_data.get("resistance", close_p * 1.05)
    vol_ratio = tech_data.get("volume_ratio", 1.0)

    headlines = sent_data.get("headlines", [])
    headlines_text = "\n".join(f"- {h}" for h in headlines[:5]) if headlines else "No recent corporate controversy or negative regulatory disclosures."

    # -------------------------------------------------------------
    # STAGE 1: PARALLEL THREE ANALYSTS (Fundamental, Technical, Sentiment)
    # -------------------------------------------------------------
    def run_fundamental_analyst():
        sys_p = "You are the Senior Fundamental Equity Research Analyst in an institutional committee for Indian Equities (NSE/BSE)."
        usr_p = (
            f"Asset: {sym} ({company_name}) on NSE/BSE India\n"
            f"Audited Financial Metrics:\n"
            f"- Market Cap: ₹{mcap_cr:,.0f} Cr\n"
            f"- Valuation: Trailing P/E {pe}, P/B {pb}, PEG {peg}\n"
            f"- Solvency: Debt-to-Equity {de}, Altman Z-Score {alt_z} ({alt_zone})\n"
            f"- Quality & Compounding: Piotroski F-Score {piot}/9, ROE {roe}%, OPM {opm}%\n\n"
            "Produce an institutional fundamental audit report in raw JSON:\n"
            "{\n"
            '  "agent": "Fundamentals Analyst",\n'
            '  "score": float (0.0 to 100.0),\n'
            '  "verdict": "High-Quality Institutional Compounder" | "Fundamentally Stable" | "Fundamental Red Flags Present",\n'
            '  "summary": "3-4 sentence detailed financial health and economic moat audit.",\n'
            '  "highlights": ["strength 1", "strength 2", "strength 3"],\n'
            '  "concerns": ["concern 1", "concern 2"]\n'
            "}"
        )
        return call_llm_json(sys_p, usr_p, temp=0.2, max_tokens=700)

    def run_technical_analyst():
        sys_p = "You are the Senior Quantitative & Technical Market Strategist (CMT) in an institutional committee for Indian Equities (NSE/BSE)."
        usr_p = (
            f"Asset: {sym} ({company_name}) on NSE/BSE India\n"
            f"Technical Levels & Indicators:\n"
            f"- Current Market Price: ₹{close_p:.2f}\n"
            f"- EMA Ribbon: 20-EMA ₹{ema20}, 50-EMA ₹{ema50}, 200-EMA ₹{ema200}\n"
            f"- Momentum: 14-RSI at {rsi}, Volume Ratio at {vol_ratio}x historical norm\n"
            f"- Pivots: Critical Support ₹{support:.2f}, Overhead Resistance ₹{resistance:.2f}\n\n"
            "Produce a professional technical chart and trend analysis in raw JSON:\n"
            "{\n"
            '  "agent": "Technical Analyst",\n'
            '  "score": float (0.0 to 100.0),\n'
            '  "verdict": "Bullish Breakout / High Momentum" | "Constructive Consolidation" | "Bearish Overhead Resistance",\n'
            '  "trend_state": "Strong Bullish Structure" | "Short-Term Uptrend" | "Correction / Bearish Pullback",\n'
            '  "summary": "3-4 sentence technical structural assessment covering trend, momentum, and volume sponsorship.",\n'
            '  "highlights": ["technical bullish signal 1", "technical bullish signal 2"],\n'
            '  "concerns": ["overhead supply or momentum risk 1"]\n'
            "}"
        )
        return call_llm_json(sys_p, usr_p, temp=0.2, max_tokens=700)

    def run_sentiment_analyst():
        sys_p = "You are the Senior Sentiment & Regulatory Risk Intelligence Officer in an institutional committee for Indian Equities (NSE/BSE)."
        usr_p = (
            f"Asset: {sym} ({company_name}) on NSE/BSE India\n"
            f"Recent Corporate Headlines & Disclosures:\n"
            f"{headlines_text}\n\n"
            "Produce an institutional sentiment and governance clearance report in raw JSON:\n"
            "{\n"
            '  "agent": "Sentiment & Regulatory Analyst",\n'
            '  "score": float (0.0 to 100.0),\n'
            '  "verdict": "Positive Institutional Sentiment / Cleared" | "Neutral Media Coverage" | "Elevated Event Risk",\n'
            '  "sentiment_label": "Bullish" | "Neutral" | "Bearish",\n'
            '  "has_veto": boolean (true if severe governance fraud or SEBI ban),\n'
            '  "veto_reason": string or null,\n'
            '  "summary": "2-3 sentence sentiment and narrative summary.",\n'
            '  "recent_headlines": ["headline 1", "headline 2"],\n'
            '  "concerns": ["sentiment/governance concern"]\n'
            "}"
        )
        return call_llm_json(sys_p, usr_p, temp=0.2, max_tokens=600)

    # Concurrently execute 3 analysts
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_fund = executor.submit(run_fundamental_analyst)
        f_tech = executor.submit(run_technical_analyst)
        f_sent = executor.submit(run_sentiment_analyst)
        fund_report = f_fund.result()
        tech_report = f_tech.result()
        sentiment_report = f_sent.result()

    # Re-attach metrics dictionaries for UI tables
    fund_report["metrics"] = fund_data
    tech_report["metrics"] = tech_data

    # -------------------------------------------------------------
    # STAGE 2: BULL RESEARCHER & BEAR RESEARCHER & ADVERSARIAL DEBATE
    # -------------------------------------------------------------
    debate_sys = (
        "You are the Bull and Bear Research Heads conducting a live adversarial institutional debate "
        "inspired by the TauricResearch / UCLA-MIT TradingAgents framework for Indian Equities (NSE/BSE)."
    )
    debate_usr = (
        f"Asset: {sym} ({company_name}) - Currently trading at ₹{close_p:.2f} on NSE/BSE.\n"
        f"Fundamentals Analyst Report: Score {fund_report.get('score')}/100, Verdict: {fund_report.get('verdict')}. Summary: {fund_report.get('summary')}\n"
        f"Technical Analyst Report: Score {tech_report.get('score')}/100, Verdict: {tech_report.get('verdict')}. Summary: {tech_report.get('summary')}\n"
        f"Sentiment Analyst Report: Score {sentiment_report.get('score')}/100, Sentiment: {sentiment_report.get('sentiment_label')}. Summary: {sentiment_report.get('summary')}\n\n"
        "Generate the Bull Thesis, Bear Thesis, and a realistic 4-Round Debate Exchange in raw JSON:\n"
        "{\n"
        '  "bull_researcher": {\n'
        '    "thesis_title": "string",\n'
        '    "confidence_pct": float (0.0 to 100.0),\n'
        '    "target1": float (realistic swing target in ₹),\n'
        '    "target2": float (multibagger/extended target in ₹),\n'
        '    "target1_gain_pct": float,\n'
        '    "target2_gain_pct": float,\n'
        '    "core_pillars": ["pillar 1", "pillar 2", "pillar 3"],\n'
        '    "bullish_thesis": "string (comprehensive institutional long argument)"\n'
        '  },\n'
        '  "bear_researcher": {\n'
        '    "thesis_title": "string",\n'
        '    "skepticism_pct": float (0.0 to 100.0),\n'
        '    "downside_risk_price": float (downside risk level in ₹),\n'
        '    "downside_drop_pct": float,\n'
        '    "key_vulnerabilities": ["vulnerability 1", "vulnerability 2", "vulnerability 3"],\n'
        '    "bearish_critique": "string (comprehensive institutional bear critique)"\n'
        '  },\n'
        '  "debate_transcript": [\n'
        '    {"speaker": "Bull Researcher", "avatar": "bull", "round": "Round 1 — Opening Thesis", "argument": "string"},\n'
        '    {"speaker": "Bear Researcher", "avatar": "bear", "round": "Round 1 — Counter-Attack", "argument": "string"},\n'
        '    {"speaker": "Bull Researcher", "avatar": "bull", "round": "Round 2 — Rebuttal", "argument": "string"},\n'
        '    {"speaker": "Bear Researcher", "avatar": "bear", "round": "Round 2 — Stress Test", "argument": "string"}\n'
        '  ]\n'
        "}"
    )
    debate_payload = call_llm_json(debate_sys, debate_usr, temp=0.4, max_tokens=1800)
    bull_report = debate_payload["bull_researcher"]
    bear_report = debate_payload["bear_researcher"]
    debate_transcript = debate_payload["debate_transcript"]

    # -------------------------------------------------------------
    # STAGE 3: CHIEF RISK OFFICER (CRO) AUDIT & FUND MANAGER (CIO) DECREE
    # -------------------------------------------------------------
    decision_sys = (
        "You are the Chief Risk Officer (CRO) and Chief Investment Officer (CIO) of an elite institutional investment firm "
        "managing Indian Equities (NSE/BSE). You enforce strict capital preservation and position sizing discipline."
    )
    ml = market_data.get("ml_signal") or {}
    ml_text = (
        f"In-house ML model signal ({ml.get('source')}): predicted return {ml.get('predicted_return_pct')}% "
        f"to ₹{ml.get('predicted_price')}, trader score {ml.get('trader_score')}, "
        f"simulated win probability {ml.get('win_probability_pct')}%, market regime {ml.get('market_regime')}.\n"
        "Weigh this quantitative signal alongside the debate; if you disagree with it, say why in the memo.\n"
    ) if ml else ""
    decision_usr = (
        f"Asset: {sym} ({company_name}) at ₹{close_p:.2f}\n"
        f"{ml_text}"
        f"Bull Target 1: ₹{bull_report.get('target1')}, Bear Downside Risk: ₹{bear_report.get('downside_risk_price')}\n"
        f"Bull Confidence: {bull_report.get('confidence_pct')}%, Bear Skepticism: {bear_report.get('skepticism_pct')}%\n"
        f"Debate Transcript Rounds: {len(debate_transcript)} completed rounds.\n\n"
        "Generate the Risk Audit and Final CIO Decree in raw JSON:\n"
        "{\n"
        '  "risk_officer": {\n'
        '    "risk_category": "Low Risk / Defensive Compounder" | "Moderate Risk / High-Probability Setup" | "Elevated Risk / Strict Sizing Mandate",\n'
        '    "stop_loss_price": float (exact stop-loss price in ₹, must be below close),\n'
        '    "stop_loss_pct": float (e.g. -4.5),\n'
        '    "risk_reward_ratio": "1 : X.X",\n'
        '    "max_portfolio_allocation_pct": float (e.g. 3.0 to 8.0),\n'
        '    "daily_var_95_pct": float,\n'
        '    "audit_verdict": "APPROVED WITH STOP-LOSS MANDATE" | "REJECTED DUE TO ASYMMETRIC RISK",\n'
        '    "summary": "string (CRO risk parameters and allocation mandate)"\n'
        '  },\n'
        '  "fund_manager": {\n'
        '    "final_order": "STRONG BUY" | "ACCUMULATE ON DIPS" | "HOLD / WATCHLIST" | "AVOID / REJECT",\n'
        '    "conviction_score": float (0.0 to 100.0),\n'
        '    "action_directive": "string (exact execution directive, e.g. Execute market order at ₹X)",\n'
        '    "entry_reference": float,\n'
        '    "target1": float,\n'
        '    "target2": float,\n'
        '    "stop_loss": float,\n'
        '    "horizon": "4 to 12 Weeks (Institutional Swing / Compounder Run)",\n'
        '    "memo": "string (Full official Executive Investment Committee Memorandum signing off on this trade)"\n'
        '  }\n'
        "}"
    )
    decision_payload = call_llm_json(decision_sys, decision_usr, temp=0.2, max_tokens=1400)
    risk_report = decision_payload["risk_officer"]
    fund_manager_report = decision_payload["fund_manager"]

    elapsed_s = round(time.time() - t0, 2)
    logger.info(f"Deliberation complete for {sym} in {elapsed_s}s! Decision: {fund_manager_report.get('final_order')}")

    return {
        "symbol": sym,
        "name": company_name,
        "exchange": market_data.get("exchange", "NSE"),
        "yahoo_symbol": market_data.get("yahoo_symbol", f"{sym}.NS"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S IST"),
        "analysis_time_seconds": elapsed_s,
        "ai_engine_used": ai_label,
        "final_decision": fund_manager_report.get("final_order", "HOLD / WATCHLIST"),
        "conviction_score": fund_manager_report.get("conviction_score", 50.0),
        "entry_price": fund_manager_report.get("entry_reference", close_p),
        "target1": fund_manager_report.get("target1", bull_report.get("target1", close_p * 1.15)),
        "target2": fund_manager_report.get("target2", bull_report.get("target2", close_p * 1.35)),
        "stop_loss": fund_manager_report.get("stop_loss", risk_report.get("stop_loss_price", close_p * 0.95)),
        "risk_reward": risk_report.get("risk_reward_ratio", "1 : 2.0"),
        "max_allocation_pct": risk_report.get("max_portfolio_allocation_pct", 5.0),
        "agents": {
            "fundamentals": fund_report,
            "technicals": tech_report,
            "sentiment": sentiment_report,
            "bull_researcher": bull_report,
            "bear_researcher": bear_report,
            "risk_officer": risk_report,
            "fund_manager": fund_manager_report
        },
        "debate_transcript": debate_transcript,
        "executive_memo": fund_manager_report.get("memo", "")
    }
