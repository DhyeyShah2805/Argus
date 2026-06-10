"""
Report Writer Agent
-------------------
Final agent: produces the polished markdown research report.
"""

import logging
import json
from datetime import datetime
from backend.agents.state import ResearchState
from backend.utils.llm import get_llm

logger = logging.getLogger(__name__)

REPORT_PROMPT = """You are an institutional equity research analyst writing a polished report.

═══════════════════════════════════════════════════════════════
DATA YOU MUST USE (do not invent anything beyond this)
═══════════════════════════════════════════════════════════════

Ticker: {ticker}
Company: {company}
Sector: {sector}
Report Date: {date}

INVESTMENT THESIS (from synthesis agent):
{thesis}

RISK CRITIQUE (from risk agent):
{risk_critique}

FINANCIAL RATIOS:
{financials}

10-K / 10-Q SUMMARY:
{filings}

EARNINGS HISTORY:
{earnings}

NEWS:
{news}

SOCIAL SENTIMENT:
{social}

INSIDER ACTIVITY:
{insider}

COMPETITIVE POSITIONING:
{competitor}

═══════════════════════════════════════════════════════════════
REPORT STRUCTURE (use these EXACT sections, in order)
═══════════════════════════════════════════════════════════════

1. `# {ticker} — Equity Research Report` with `*Generated: {date}*` underneath
2. `## Executive Summary` — 2-3 sentences ending with recommendation and confidence
3. `## Investment Thesis` with `### Bull Case` and `### Bear Case` subsections (bullet points from thesis data)
4. `## Financial Health` — Markdown table comparing AAPL to peer averages from competitor data
5. `## Recent Earnings` — bullet list from earnings data. DO NOT duplicate quarters. DO NOT invent quarters.
6. `## Filings & Disclosures` — bullet list of key items from the 10-K/10-Q summary. ALWAYS include the actual content. Never write "omitted" or "see above".
7. `## Market Sentiment` with `### News` and `### Social Media` subsections
8. `## Insider Activity` — describe activity if transaction counts > 0, else write exactly "No notable insider activity in the last 90 days."
9. `## Competitive Positioning` — Markdown table using EXACT ticker names from competitor data
10. `## Risk Factors & Critique` — bullet list of specific risks from the risk critique
11. `## Final Recommendation` — ONE sentence: "[BUY/HOLD/SELL] with [X]% confidence over a [short/medium/long]-term horizon."
12. `## Sources` — bullet list of actual sources used: SEC EDGAR (10-K/10-Q), yfinance, Finnhub, Tavily News, FinBERT. Only include sources that returned non-empty data.
13. `---` followed by `*Disclaimer: Educational research only, not investment advice.*`

═══════════════════════════════════════════════════════════════
CRITICAL RULES — VIOLATING THESE INVALIDATES THE REPORT
═══════════════════════════════════════════════════════════════

1. NEVER invent numbers. Use ONLY the numbers in the data above.
2. NEVER mention COVID-19, specific historical events, or years not in the data.
3. NEVER mention social media activity (Twitter, LinkedIn, follower counts) unless social_data explicitly contains posts. If social_data shows N/A or 0 mentions, write "No significant social media discussion detected."
4. If bull and bear cases mention the same metric (e.g. P/E), the VALUE must be identical in both sections. Never say "35" in one and "30" in another.
5. NEVER write placeholder text like "(list all sources)", "see above", "TBD", or "20XX".
6. NEVER duplicate earnings quarters in the Recent Earnings section.
7. Use the EXACT peer ticker names from competitor data — never relabel them (no "NVIDIA (META)" — that is wrong).
8. Each section uses ONLY data from its corresponding source. Filings section uses filings data. Earnings uses earnings data. Etc.
9. If a section's data is empty or N/A, write "No data available." DO NOT fabricate content.
10. Use the date {date} for the report header — do not use placeholder years.
11. Be specific. Cite real numbers. No filler sentences.

Now generate the report.
"""


def report_writer(state: ResearchState) -> dict:
    logger.info(f"[Writer] Generating report for {state['ticker']}")

    llm = get_llm(json_mode=False)
    financials = state.get("financials_data", {})

    prompt = REPORT_PROMPT.format(
        ticker=state["ticker"],
        company=financials.get("company_name", state["ticker"]),
        sector=financials.get("sector", "N/A"),
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        thesis=json.dumps(state.get("thesis", {}), indent=2),
        risk_critique=json.dumps(state.get("risk_critique", {}), indent=2),
        financials=json.dumps(financials.get("ratios", {}), indent=2),
        filings=state.get("filings_data", {}).get("summary", "N/A")[:1500],
        earnings=state.get("earnings_data", {}).get("analysis", "N/A"),
        news=_format_news(state.get("news_data", {})),
        social=_format_social(state.get("social_data", {})),
        insider=_format_insider(state.get("insider_data", {})),
        competitor=_format_competitor(state.get("competitor_data", {})),
    )

    response = llm.invoke(prompt)
    report = response.content if hasattr(response, "content") else str(response)

    metadata = {
        "ticker": state["ticker"],
        "company": financials.get("company_name"),
        "generated_at": datetime.utcnow().isoformat(),
        "word_count": len(report.split()),
        "iterations": state["iteration"],
        "recommendation": state.get("thesis", {}).get("recommendation"),
        "confidence": state.get("thesis", {}).get("confidence"),
        "sources_used": _list_sources(state),
    }

    return {"final_report": report, "report_metadata": metadata}


def _format_news(d: dict) -> str:
    if not d or d.get("status"):
        return "No news data available."
    return (
        f"Articles: {d.get('article_count')}, "
        f"avg sentiment: {d.get('avg_sentiment')}, "
        f"positive: {d.get('positive_count')}, negative: {d.get('negative_count')}"
    )


def _format_social(d: dict) -> str:
    if not d or d.get("status") or d.get("mention_count", 0) == 0:
        return "No social media data available (Reddit returned 0 posts or auth failed)."
    return (
        f"Mentions: {d.get('mention_count')}, "
        f"avg sentiment: {d.get('avg_sentiment')}, "
        f"engagement: {d.get('total_engagement')}"
    )


def _format_insider(d: dict) -> str:
    if not d or d.get("status"):
        return "No insider data available."
    buy_count = d.get("buy_count", 0)
    sell_count = d.get("sell_count", 0)
    if buy_count == 0 and sell_count == 0:
        return "No insider transactions in the last 90 days."
    return (
        f"Buys: {buy_count} ({d.get('shares_bought')} sh) | "
        f"Sells: {sell_count} ({d.get('shares_sold')} sh) | "
        f"Signal: {d.get('signal')}"
    )


def _format_competitor(d: dict) -> str:
    if not d or d.get("status"):
        return "No competitor data available."
    peers = d.get("peers", [])[:5]
    avg_pe = d.get("avg_peer_pe")
    avg_margin = d.get("avg_peer_margin")

    lines = [f"PEER AVERAGES: P/E={avg_pe}, Profit Margin={avg_margin}"]
    lines.append("INDIVIDUAL PEERS:")
    for p in peers:
        lines.append(
            f"  {p['ticker']}: P/E {p.get('pe_ratio')}, "
            f"Margin {p.get('profit_margin')}, Market Cap {p.get('market_cap')}"
        )
    return "\n".join(lines)


def _list_sources(state: dict) -> list:
    sources = []
    for key in ["filings_data", "financials_data", "news_data",
                "social_data", "earnings_data", "insider_data", "competitor_data"]:
        d = state.get(key, {})
        if d.get("source"):
            sources.append(d["source"])
    return sources