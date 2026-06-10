"""
Backtest Eval
-------------
Run the agent on 10 tickers, then check its recommendations
against actual 30-day forward returns.

Run: python scripts/backtest_eval.py
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf
from backend.agents.graph import run_research

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "META",
                "GOOGL", "AMZN", "JPM", "PFE", "DIS"]


def actual_30d_return(ticker: str) -> float:
    """Return 30-day forward return %."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="60d")
    if len(hist) < 30:
        return None
    today = hist["Close"][-1]
    month_ago = hist["Close"][-30]
    return ((today - month_ago) / month_ago) * 100


async def run_eval():
    results = []

    for ticker in TEST_TICKERS:
        logger.info(f"\n{'='*50}\nEvaluating {ticker}\n{'='*50}")
        try:
            state = await run_research(ticker)
            thesis = state.get("thesis", {})
            rec = thesis.get("recommendation", "—")
            conf = thesis.get("confidence", 0)
            actual = actual_30d_return(ticker)

            # Did the recommendation align with actual direction?
            if actual is not None:
                aligned = (
                    (rec == "BUY" and actual > 0) or
                    (rec == "SELL" and actual < 0) or
                    (rec == "HOLD" and abs(actual) < 5)
                )
            else:
                aligned = None

            results.append({
                "ticker": ticker,
                "recommendation": rec,
                "confidence": conf,
                "actual_30d_return_pct": actual,
                "aligned": aligned,
            })

            logger.info(f"  Rec: {rec} ({conf}%) | Actual: {actual:.2f}% | Aligned: {aligned}")

        except Exception as e:
            logger.error(f"  Failed: {e}")
            results.append({"ticker": ticker, "error": str(e)})

    # Summary
    valid = [r for r in results if r.get("aligned") is not None]
    if valid:
        accuracy = sum(1 for r in valid if r["aligned"]) / len(valid) * 100
        avg_conf = sum(r["confidence"] for r in valid) / len(valid)
        print(f"\n{'='*50}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*50}")
        print(f"Tickers evaluated: {len(valid)}/{len(TEST_TICKERS)}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Avg confidence: {avg_conf:.1f}%")

    out = Path("./data/reports/backtest_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")


if __name__ == "__main__":
    asyncio.run(run_eval())
