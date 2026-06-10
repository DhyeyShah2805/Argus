"""
Filings Sub-Agent
-----------------
Pulls SEC filings (10-K, 10-Q, recent 8-K) via EDGAR,
chunks them, summarizes key sections, and extracts risk factors.
"""

import os
import logging
import re
from pathlib import Path
from sec_edgar_downloader import Downloader
from backend.agents.state import ResearchState
from backend.utils.llm import get_llm

logger = logging.getLogger(__name__)

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "Research Agent research@example.com")
CACHE_DIR = Path("./data/cache/sec")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


FILINGS_SUMMARY_PROMPT = """You are a financial analyst summarizing SEC filings.

Below is content from a recent 10-K / 10-Q filing for {ticker}.

Filing text (truncated):
{text}

Extract and summarize:
1. Business overview (2-3 sentences)
2. Revenue drivers (key segments)
3. Top 5 risk factors (bullet points)
4. Any unusual disclosures or red flags

Be concrete. Cite specific numbers where you see them.
"""


def filings_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"filings_data": {"status": "skipped - no ticker"}}

    logger.info(f"[Filings] Fetching SEC filings for {ticker}")

    try:
        name, email = _parse_user_agent(SEC_USER_AGENT)
        dl = Downloader(name, email, str(CACHE_DIR))

        # Pull most recent 10-K and 10-Q
        dl.get("10-K", ticker, limit=1)
        dl.get("10-Q", ticker, limit=1)

        # Read the filing text
        filing_text = _read_latest_filing(ticker)
        if not filing_text:
            return {"filings_data": {"status": "no filings found"}}

        # Summarize via LLM
        llm = get_llm(json_mode=False)
        prompt = FILINGS_SUMMARY_PROMPT.format(
            ticker=ticker, text=filing_text[:6000]
        )
        response = llm.invoke(prompt)
        summary = response.content if hasattr(response, "content") else str(response)

        # Extract risk section via simple regex
        risk_section = _extract_risk_section(filing_text)

        return {
            "filings_data": {
                "summary": summary,
                "risk_factors": risk_section[:3000],
                "source": f"SEC EDGAR — {ticker} 10-K/10-Q",
            }
        }

    except Exception as e:
        logger.error(f"[Filings] Failed: {e}")
        return {"filings_data": {"status": "error", "error": str(e)}}


def _parse_user_agent(ua: str):
    """SEC requires 'Name email' format."""
    parts = ua.split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return "Research Agent", "research@example.com"


def _read_latest_filing(ticker: str) -> str:
    """Read concatenated text from most recent filing."""
    base = CACHE_DIR / "sec-edgar-filings" / ticker
    if not base.exists():
        return ""

    for filing_type in ["10-K", "10-Q"]:
        ftype_dir = base / filing_type
        if ftype_dir.exists():
            # Get most recent subdir
            subdirs = sorted(ftype_dir.iterdir(), reverse=True)
            if subdirs:
                for f in subdirs[0].glob("*.txt"):
                    return f.read_text(errors="ignore")
    return ""


def _extract_risk_section(text: str) -> str:
    """Find ITEM 1A. RISK FACTORS section."""
    match = re.search(
        r"(?i)item\s*1a\.?\s*risk\s*factors(.{500,5000}?)(?=item\s*1b|item\s*2)",
        text,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""
