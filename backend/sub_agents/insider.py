"""
Insider Trading Sub-Agent
-------------------------
Pulls Form 4 filings via Finnhub (free tier supports this)
to track executive/director buying and selling.

Strong signal: cluster buying = bullish, cluster selling = neutral-to-bearish
(execs sell for many reasons, but buying is almost always conviction).
"""

import os
import logging
import finnhub
from datetime import datetime, timedelta
from backend.agents.state import ResearchState

logger = logging.getLogger(__name__)


def insider_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"insider_data": {"status": "skipped"}}

    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if not finnhub_key:
        return {"insider_data": {"status": "no FINNHUB_API_KEY"}}

    logger.info(f"[Insider] Pulling Form 4 filings for {ticker}")

    try:
        fh = finnhub.Client(api_key=finnhub_key)

        # 90 days of transactions
        end = datetime.now()
        start = end - timedelta(days=90)
        result = fh.stock_insider_transactions(
            ticker,
            _from=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
        )

        transactions = result.get("data", [])

        # Aggregate buys vs sells
        buy_shares = 0
        sell_shares = 0
        buy_count = 0
        sell_count = 0
        notable = []

        for txn in transactions:
            shares = txn.get("share", 0)
            txn_code = txn.get("transactionCode", "")
            # P = Purchase, S = Sale, A = Award
            if txn_code in ("P", "A"):
                buy_shares += abs(shares)
                buy_count += 1
            elif txn_code == "S":
                sell_shares += abs(shares)
                sell_count += 1

            notable.append({
                "name": txn.get("name"),
                "date": txn.get("transactionDate"),
                "shares": shares,
                "price": txn.get("transactionPrice"),
                "code": txn_code,
            })

        # Signal interpretation
        net_shares = buy_shares - sell_shares
        if buy_count >= 3 and buy_shares > sell_shares * 2:
            signal = "bullish_cluster_buying"
        elif sell_count >= 5 and sell_shares > buy_shares * 3:
            signal = "concerning_cluster_selling"
        else:
            signal = "neutral"

        return {
            "insider_data": {
                "total_transactions": len(transactions),
                "buy_count": buy_count,
                "sell_count": sell_count,
                "shares_bought": buy_shares,
                "shares_sold": sell_shares,
                "net_shares": net_shares,
                "signal": signal,
                "notable_transactions": notable[:10],
                "period": "Last 90 days",
                "source": "Finnhub (SEC Form 4)",
            }
        }

    except Exception as e:
        logger.error(f"[Insider] Failed: {e}")
        return {"insider_data": {"status": "error", "error": str(e)}}
