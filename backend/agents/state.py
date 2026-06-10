"""
Shared state schema for the trading research agent.
All sub-agents read from + write to this TypedDict in parallel.
"""

from typing import TypedDict, List, Dict, Optional


class ResearchState(TypedDict):
    # Input
    ticker: str
    sector: Optional[str]
    query_context: str          # e.g. "long-term investor" / "short-term trader"

    # Orchestrator output
    research_plan: str
    sub_agents_to_run: List[str]

    # Parallel sub-agent outputs
    filings_data: Dict           # {10K_summary, 10Q_summary, 8K_recent, risks}
    financials_data: Dict        # {ratios, trends, valuation_metrics}
    news_data: Dict              # {articles, sentiment_score, key_themes}
    social_data: Dict            # {reddit_sentiment, mention_volume, themes}
    earnings_data: Dict          # {transcript_summary, tone_score, q&a_highlights}
    insider_data: Dict           # {recent_trades, net_activity, signal}
    competitor_data: Dict        # {peers, relative_performance, positioning}

    # Synthesis
    thesis: Dict                 # {bull_case, bear_case, key_drivers, confidence}

    # Risk critique
    risk_critique: Dict          # {blind_spots, contradictions, severity}
    critique_passed: bool

    # Final report
    final_report: str
    report_metadata: Dict        # {ticker, date, word_count, sources, charts}

    # Loop control
    iteration: int
    max_iterations: int
