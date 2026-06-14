"""
Risk Agent
----------
Adversarial critique of the thesis.
Surfaces blind spots, internal contradictions, and missing risk factors.
Can trigger a loop back to the orchestrator for additional research.
"""

import os
import json
import logging
from backend.agents.state import ResearchState
from backend.utils.llm import get_llm

logger = logging.getLogger(__name__)
MAX_ITERATIONS = int(os.getenv("MAX_CRITIQUE_ITERATIONS", 2))

RISK_PROMPT = """You are a skeptical risk analyst. Tear apart the following thesis.

Ticker: {ticker}
Thesis: {thesis}

Source data summary:
- Financials: P/E {pe}, Margin {margin}, Revenue Growth {growth}
- News sentiment: {news_sent}
- Reddit sentiment: {reddit_sent}
- Insider signal: {insider}

Identify:
1. CONTRADICTIONS between data sources (e.g. bullish thesis but heavy insider selling)
2. BLIND SPOTS — what's missing from this analysis?
3. CONFIRMATION BIAS — places the thesis ignores contrary data
4. MACRO RISKS not addressed

Return ONLY valid JSON:
{{
  "contradictions": ["..."],
  "blind_spots": ["..."],
  "confirmation_bias_issues": ["..."],
  "macro_risks": ["..."],
  "severity": <0-10>,
  "passed": <true if severity <= 4 else false>,
  "summary": "<one line assessment>"
}}
"""


def risk_agent(state: ResearchState) -> dict:
    logger.info(f"[Risk] Critiquing thesis for {state['ticker']} (iter {state['iteration']})")

    llm = get_llm(json_mode=True)
    thesis = state.get("thesis", {})
    financials = state.get("financials_data", {})
    ratios = financials.get("ratios", {})

    # Strip the calibrator's internal bookkeeping keys so they
    # don't leak code-style strings (e.g. 'extremely_overvalued')
    # into the LLM's critique.
    INTERNAL_KEYS = {
        "signal_flags", "calibration_reasoning", "calibration_applied",
        "original_recommendation", "original_confidence",
    }
    clean_thesis = {k: v for k, v in thesis.items() if k not in INTERNAL_KEYS}

    prompt = RISK_PROMPT.format(
        ticker=state["ticker"],
        thesis=json.dumps(clean_thesis, indent=2),
        pe=ratios.get("P/E (trailing)"),
        margin=ratios.get("Profit Margin"),
        growth=ratios.get("Revenue Growth (YoY)"),
        news_sent=state.get("news_data", {}).get("avg_sentiment"),
        reddit_sent=state.get("social_data", {}).get("avg_sentiment"),
        insider=state.get("insider_data", {}).get("signal", "N/A"),
    )

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        clean = text.replace("```json", "").replace("```", "").strip()
        critique = json.loads(clean)
        passed = critique.get("severity", 10) <= 4
    except Exception as e:
        logger.warning(f"[Risk] Parse failed: {e}")
        critique = {"summary": "Critique parse failed", "severity": 5}
        passed = True   # don't loop forever on parse fail

    return {
        "risk_critique": critique,
        "critique_passed": passed,
        "iteration": state["iteration"] + 1,
    }