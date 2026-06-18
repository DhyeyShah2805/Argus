"""
Earnings Sub-Agent
------------------
Pulls latest earnings data via yfinance + Finnhub,
analyzes guidance and management tone via LLM.

For free tier: uses yfinance earnings_dates and quarterly_earnings.
For premium: Financial Modeling Prep has transcripts.
"""

import os
import logging
import yfinance as yf
import finnhub
from backend.agents.state import ResearchState
from backend.utils.llm import get_llm
from backend.ml.finbert import score_sentiment

logger = logging.getLogger(__name__)

EARNINGS_ANALYSIS_PROMPT = """You are analyzing earnings results for {ticker}.

Recent quarterly earnings data:
{earnings_summary}

Provide:
1. Earnings beat/miss vs estimates (with specifics)
2. Revenue trend
3. Most important takeaway
4. Risk or red flag (if any)

Keep it concise (3-4 sentences total).
"""


def earnings_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"earnings_data": {"status": "skipped"}}

    logger.info(f"[Earnings] Fetching for {ticker}")

    try:
        stock = yf.Ticker(ticker)

        # Get recent earnings
        earnings_dates = stock.earnings_dates
        if earnings_dates is None or len(earnings_dates) == 0:
            return {"earnings_data": {"status": "no earnings data"}}

        # Most recent past earnings
        past = earnings_dates.dropna(subset=["Reported EPS"]).head(4)

        earnings_summary = []
        seen_quarters = set()
        for date, row in past.iterrows():
            # Dedupe by year-quarter
            quarter_key = str(date.date())
            if quarter_key in seen_quarters:
                continue
            seen_quarters.add(quarter_key)
            
            reported = float(row.get("Reported EPS")) if row.get("Reported EPS") is not None else None
            estimate = float(row.get("EPS Estimate")) if row.get("EPS Estimate") is not None else None

            # Recompute surprise ourselves — yfinance's Surprise(%) divides by the
            # signed estimate, which explodes/flips sign when estimates are negative
            # (e.g. Boeing). Use abs() in the denominator to keep direction correct,
            # and cap extreme values that occur when the estimate is near zero.
            if reported is not None and estimate is not None and estimate != 0:
                raw = ((reported - estimate) / abs(estimate)) * 100
                surprise_pct = round(max(-999, min(999, raw)), 2)
            else:
                surprise_pct = None

            earnings_summary.append({
                "date": str(date.date()),
                "quarter": quarter_key,
                "reported_eps": reported,
                "estimated_eps": estimate,
                "surprise_pct": surprise_pct,
            })

        # LLM tone analysis
        llm = get_llm(json_mode=False)
        summary_text = "\n".join([
            f"  {e['date']}: EPS reported {e['reported_eps']} vs est {e['estimated_eps']} "
            f"(surprise: {e['surprise_pct']}%)"
            for e in earnings_summary
        ])

        analysis = ""
        try:
            response = llm.invoke(EARNINGS_ANALYSIS_PROMPT.format(
                ticker=ticker, earnings_summary=summary_text
            ))
            analysis = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.warning(f"[Earnings] LLM analysis failed: {e}")

        # Tone via FinBERT on the analysis itself
        tone = score_sentiment(analysis)

        # Optional: Finnhub for transcript snippets
        transcript_excerpt = ""
        finnhub_key = os.getenv("FINNHUB_API_KEY")
        if finnhub_key:
            try:
                fh = finnhub.Client(api_key=finnhub_key)
                transcripts = fh.transcripts_list(ticker)
                if transcripts.get("transcripts"):
                    latest_id = transcripts["transcripts"][0]["id"]
                    t = fh.transcripts(latest_id)
                    transcript_excerpt = str(t.get("transcript", []))[:2000]
            except Exception as e:
                logger.warning(f"[Earnings] Finnhub transcript failed: {e}")

        return {
            "earnings_data": {
                "recent_earnings": earnings_summary,
                "analysis": analysis,
                "tone": tone["label"],
                "tone_score": tone["score"],
                "transcript_excerpt": transcript_excerpt,
                "source": "yfinance + Finnhub",
            }
        }

    except Exception as e:
        logger.error(f"[Earnings] Failed: {e}")
        return {"earnings_data": {"status": "error", "error": str(e)}}
