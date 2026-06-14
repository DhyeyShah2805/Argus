"""
Calibration Agent
-----------------
Post-LLM rule layer. Applies deterministic finance heuristics
to downgrade recommendations when underlying data shows weakness.

This corrects for small-LLM BUY bias by introducing rules that
cannot be over-ridden by model defaults.

Rule logic (in order):
  1. Strong sell signal      → force SELL
  2. Multiple weakness flags → downgrade BUY to HOLD
  3. Insider selling cluster → downgrade BUY to HOLD
  4. Otherwise               → keep LLM's recommendation
"""

import logging
from backend.agents.state import ResearchState

logger = logging.getLogger(__name__)


def calibrator_agent(state: ResearchState) -> dict:
    thesis = dict(state.get("thesis", {}))   # copy so we don't mutate
    original_rec = thesis.get("recommendation", "HOLD")
    original_conf = thesis.get("confidence", 50)

    flags = _evaluate_signals(state)
    new_rec, new_conf, reasoning = _apply_rules(
        original_rec, original_conf, flags
    )

    if new_rec != original_rec:
        logger.info(
            f"[Calibrator] {state['ticker']}: {original_rec} ({original_conf}%) "
            f"→ {new_rec} ({new_conf}%) — {reasoning}"
        )
    else:
        logger.info(f"[Calibrator] {state['ticker']}: kept {original_rec} ({original_conf}%)")

    thesis["recommendation"] = new_rec
    thesis["confidence"] = new_conf
    thesis["calibration_applied"] = (new_rec != original_rec)
    thesis["calibration_reasoning"] = reasoning
    thesis["original_recommendation"] = original_rec
    thesis["original_confidence"] = original_conf
    thesis["signal_flags"] = flags

    return {"thesis": thesis}


# ─── Signal Evaluation ──────────────────────────────────────────

def _evaluate_signals(state: ResearchState) -> dict:
    """Extract binary risk signals from the underlying data."""
    flags = {}

    # News sentiment
    news = state.get("news_data", {})
    news_sent = news.get("avg_sentiment")
    flags["news_negative"] = bool(news_sent is not None and news_sent < -0.15)
    flags["news_very_negative"] = bool(news_sent is not None and news_sent < -0.30)

    # Social sentiment (when available)
    social = state.get("social_data", {})
    social_sent = social.get("avg_sentiment")
    flags["social_negative"] = bool(
        social_sent is not None and social_sent < -0.15
        and social.get("mention_count", 0) > 0
    )

    # Earnings weakness — look at most recent quarter surprise
    earnings = state.get("earnings_data", {})
    recent = earnings.get("recent_earnings", [])
    if recent:
        latest_surprise = recent[0].get("surprise_pct")
        flags["earnings_miss"] = bool(
            latest_surprise is not None and latest_surprise < -1
        )
        flags["earnings_big_miss"] = bool(
            latest_surprise is not None and latest_surprise < -5
        )
        # Also flag if multiple recent misses
        misses = sum(
            1 for e in recent[:4]
            if e.get("surprise_pct") is not None and e.get("surprise_pct") < 0
        )
        flags["multiple_misses"] = bool(misses >= 2)
    else:
        flags["earnings_miss"] = False
        flags["earnings_big_miss"] = False
        flags["multiple_misses"] = False

    # Insider selling
    insider = state.get("insider_data", {})
    flags["insider_selling"] = bool(
        insider.get("signal") == "concerning_cluster_selling"
    )

    # Valuation — high P/E vs peers
    financials = state.get("financials_data", {})
    ratios = financials.get("ratios", {})
    pe = ratios.get("P/E (trailing)")

    competitor = state.get("competitor_data", {})
    peer_pe = competitor.get("avg_peer_pe")

    flags["overvalued_vs_peers"] = bool(
        pe is not None and peer_pe is not None
        and pe > peer_pe * 1.5
    )
    flags["extremely_overvalued"] = bool(
        pe is not None and peer_pe is not None
        and pe > peer_pe * 3
    )

    # Negative revenue growth
    rev_growth = ratios.get("Revenue Growth (YoY)")
    flags["negative_growth"] = bool(
        rev_growth is not None and rev_growth < 0
    )

    # Risk critic severity (if it already ran)
    risk = state.get("risk_critique", {})
    severity = risk.get("severity")
    flags["high_risk_severity"] = bool(
        severity is not None and severity >= 7
    )

    return flags


# ─── Rule Application ───────────────────────────────────────────

def _apply_rules(rec: str, conf: int, flags: dict) -> tuple:
    """
    Apply downgrade rules. Returns (new_rec, new_conf, reasoning_string).

    Rules are evaluated in priority order. First match wins.
    """
    rec = (rec or "HOLD").upper()

    # ── Tier 1: SELL signals ────────────────────────────
    # Multiple severe negatives → force SELL
    sell_signals = sum([
        flags["earnings_big_miss"],
        flags["news_very_negative"],
        flags["insider_selling"],
        flags["extremely_overvalued"],
        flags["negative_growth"],
    ])
    if sell_signals >= 3:
        return ("SELL", max(60, conf - 10),
                f"Three+ severe negative signals ({sell_signals} flagged)")

    # ── Tier 2: HOLD signals ────────────────────────────
    # Multiple moderate negatives → downgrade BUY to HOLD
    hold_signals = sum([
        flags["earnings_miss"],
        flags["news_negative"],
        flags["multiple_misses"],
        flags["overvalued_vs_peers"],
        flags["insider_selling"],
        flags["high_risk_severity"],
        flags["social_negative"],
    ])

    if rec == "BUY" and hold_signals >= 4:
        return ("HOLD", max(50, conf - 15),
                f"BUY downgraded to HOLD — {hold_signals} weakness signals")

    # ── Tier 3: Single strong negative → HOLD ──────────
    severe_count = sum([
        flags["earnings_big_miss"],
        flags["news_very_negative"],
        flags["extremely_overvalued"],
    ])
    if rec == "BUY" and severe_count >= 2:
        return ("HOLD", max(50, conf - 10),
                f"BUY downgraded — {severe_count} severe weakness signals")

    # ── No calibration ─────────────────────────────────
    return (rec, conf, "No calibration applied — signals support LLM recommendation")