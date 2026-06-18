"""
Synthesis Agent
---------------
Combines all sub-agent outputs into a structured
investment thesis (bull case, bear case, key drivers).
"""

import json
import logging
from backend.agents.state import ResearchState
from backend.utils.llm import get_llm

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """You are a senior equity research analyst. Synthesize the following multi-source research into a balanced investment thesis.

═══════════════════════════════════════
DATA AVAILABLE (use ONLY this — do not invent)
═══════════════════════════════════════

Target: {ticker}

FINANCIALS:
{financials}

FILINGS SUMMARY:
{filings}

EARNINGS:
{earnings}

NEWS SENTIMENT:
Average sentiment: {news_sentiment}
{news_summary}

SOCIAL SENTIMENT:
Reddit avg sentiment: {social_sentiment}
Mention volume: {mention_count}

INSIDER ACTIVITY:
{insider}

COMPETITIVE POSITIONING:
{competitor}

═══════════════════════════════════════
HARD RULES — VIOLATING ANY OF THESE INVALIDATES THE OUTPUT
═══════════════════════════════════════

1. NEVER invent numbers. Every number in your output must come from the data above.
2. NEVER mention years, events, or trends not in the data (no "COVID-19", no "during 2020", no "recent recession").
3. NEVER contradict yourself between bull and bear case. If P/E is 35, it is 35 in both sections.
4. The SAME metric must have the SAME value everywhere it appears.
5. NEVER mention social media activity, follower counts, or Twitter/LinkedIn unless social_data explicitly contains it.
6. NEVER mention insider trades unless insider_data has actual transaction counts > 0.
7. If a peer ratio is not provided in the data, do NOT compare to it. Skip the comparison.
8. For the bear case, use ONLY: actual data weaknesses (negative growth, overvaluation, earnings misses, insider selling), and these generic risks if relevant: interest rates, regulation, competition, supply chain. NO specific historical events. NO COVID-19. NO pandemics.

═══════════════════════════════════════
INTERPRETATION RULES (basic finance — do not violate)
═══════════════════════════════════════

- Higher P/E than peers → growth premium OR overvaluation (state which based on growth rate)
- Lower P/E than peers → undervaluation OR weak prospects (state which based on margins)
- Higher profit margin than peers → competitive advantage
- Higher Debt/Equity than peers → higher financial risk
- Positive insider buying cluster → bullish signal
- Negative revenue growth → bearish signal
- Do not contradict basic finance principles.

═══════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════
CRITICAL REMINDER: Do NOT mention COVID-19, the pandemic, 2020, lockdowns, or any historical event not explicitly in the data above. The bear case must use ONLY weaknesses visible in the numbers (negative growth, high P/E, earnings misses, insider selling) plus generic risks (competition, regulation, interest rates). Mentioning COVID-19 invalidates the entire output.
Return ONLY valid JSON, no preamble:
{{
  "bull_case": ["specific argument with real number 1", "specific argument with real number 2", "specific argument with real number 3"],
  "bear_case": ["specific risk 1", "specific risk 2", "specific risk 3"],
  "key_drivers": ["driver 1", "driver 2"],
  "recommendation": "BUY|HOLD|SELL",
  "confidence": <0-100>,
  "time_horizon": "short|medium|long",
  "summary": "<2 sentence overall summary using only real data>"
}}
"""


def synthesis_agent(state: ResearchState) -> dict:
    logger.info(f"[Synthesis] Building thesis for {state['ticker']}")

    llm = get_llm(json_mode=True)
    prompt = SYNTHESIS_PROMPT.format(
        ticker=state["ticker"],
        financials=_summarize_financials(state.get("financials_data", {})),
        filings=state.get("filings_data", {}).get("summary", "N/A")[:1500],
        earnings=state.get("earnings_data", {}).get("analysis", "N/A"),
        news_sentiment=state.get("news_data", {}).get("avg_sentiment", "N/A"),
        news_summary=_summarize_news(state.get("news_data", {})),
        social_sentiment=state.get("social_data", {}).get("avg_sentiment", "N/A"),
        mention_count=state.get("social_data", {}).get("mention_count", 0),
        insider=_summarize_insider(state.get("insider_data", {})),
        competitor=_summarize_competitors(state.get("competitor_data", {})),
    )

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        clean = text.replace("```json", "").replace("```", "").strip()
        thesis = json.loads(clean)
    except Exception as e:
        logger.warning(f"[Synthesis] Parse failed: {e}")
        thesis = {
            "bull_case": ["Could not parse thesis"],
            "bear_case": [],
            "recommendation": "HOLD",
            "confidence": 0,
            "summary": "Synthesis failed — see individual agent outputs.",
        }

    return {"thesis": thesis}


def _summarize_financials(d: dict) -> str:
    if not d or d.get("status") == "error":
        return "N/A"
    ratios = d.get("ratios", {})
    return (
        f"Market cap: ${d.get('market_cap', 0):,.0f}\n"
        f"Price: ${d.get('current_price')} (1y: {d.get('price_change_1y_pct')}%)\n"
        f"P/E: {ratios.get('P/E (trailing)')}, P/S: {ratios.get('P/S')}\n"
        f"ROE: {ratios.get('ROE')}, Profit Margin: {ratios.get('Profit Margin')}\n"
        f"Revenue Growth: {ratios.get('Revenue Growth (YoY)')}\n"
        f"Analyst Target: ${d.get('analyst_target')} ({d.get('analyst_recommendation')})"
    )


def _summarize_news(d: dict) -> str:
    if not d or d.get("status") == "error":
        return "N/A"
    articles = d.get("articles", [])[:3]
    return "\n".join([
        f"- [{a.get('sentiment')}] {a.get('title')}"
        for a in articles
    ])


def _summarize_insider(d: dict) -> str:
    if not d or d.get("status"):
        return "No insider data available."
    buy_count = d.get("buy_count", 0)
    sell_count = d.get("sell_count", 0)
    if buy_count == 0 and sell_count == 0:
        return "No insider transactions in the last 90 days."
    return (
        f"Buys: {buy_count} ({d.get('shares_bought')} shares) | "
        f"Sells: {sell_count} ({d.get('shares_sold')} shares) | "
        f"Signal: {d.get('signal')}"
    )


def _summarize_competitors(d: dict) -> str:
    if not d or d.get("status"):
        return "N/A"
    avg_pe = d.get("avg_peer_pe")
    avg_margin = d.get("avg_peer_margin")
    peers = d.get("peers", [])[:5]
    
    lines = [f"PEER AVERAGES: P/E={avg_pe}, Profit Margin={avg_margin}"]
    lines.append("INDIVIDUAL PEERS:")
    for p in peers:
        lines.append(
            f"  {p['ticker']}: P/E {p.get('pe_ratio')}, Margin {p.get('profit_margin')}"
        )
    return "\n".join(lines)