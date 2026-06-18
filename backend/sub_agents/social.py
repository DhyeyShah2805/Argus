"""
Social Sub-Agent
----------------
Pulls recent messages from StockTwits ($TICKER streams),
scores aggregate sentiment via FinBERT, and computes
mention volume + bullish/bearish breakdown.

StockTwits is purpose-built for stock chatter and needs no auth
(public API), making it a better fit than Reddit for this use case.
"""

import logging
import httpx
from backend.agents.state import ResearchState
from backend.ml.finbert import batch_score

logger = logging.getLogger(__name__)

STOCKTWITS_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"


def social_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"social_data": {"status": "skipped"}}

    logger.info(f"[Social] Pulling StockTwits for {ticker}")

    try:
        resp = httpx.get(
            STOCKTWITS_URL.format(ticker=ticker),
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (research agent)"},
        )

        if resp.status_code == 404:
            return {"social_data": {"mention_count": 0, "status": "ticker not found on StockTwits"}}
        if resp.status_code == 429:
            return {"social_data": {"mention_count": 0, "status": "rate limited"}}
        resp.raise_for_status()

        messages = resp.json().get("messages", [])
        if not messages:
            return {"social_data": {"mention_count": 0, "status": "no messages"}}

        posts = []
        native_bull = 0
        native_bear = 0

        for msg in messages:
            body = msg.get("body", "")
            # StockTwits users can self-tag Bullish/Bearish
            sentiment_tag = (msg.get("entities", {}) or {}).get("sentiment") or {}
            tag = (sentiment_tag.get("basic") or "").lower()
            if tag == "bullish":
                native_bull += 1
            elif tag == "bearish":
                native_bear += 1

            posts.append({
                "body": body[:300],
                "user": msg.get("user", {}).get("username"),
                "created": msg.get("created_at"),
                "native_tag": tag or "none",
                "likes": (msg.get("likes", {}) or {}).get("total", 0),
            })

        # FinBERT sentiment on message bodies (batch)
        texts = [p["body"] for p in posts if p["body"]]
        sentiments = batch_score(texts) if texts else []
        avg_finbert = (
            sum(s["score"] for s in sentiments) / len(sentiments)
            if sentiments else 0.0
        )

        # Top posts by engagement
        top_posts = sorted(posts, key=lambda p: p["likes"], reverse=True)[:5]

        return {
            "social_data": {
                "mention_count": len(messages),
                "avg_sentiment": round(avg_finbert, 3),
                "native_bullish": native_bull,
                "native_bearish": native_bear,
                "native_sentiment_ratio": (
                    round(native_bull / (native_bull + native_bear), 2)
                    if (native_bull + native_bear) > 0 else None
                ),
                "top_posts": top_posts,
                "source": "StockTwits + FinBERT",
            }
        }

    except Exception as e:
        logger.error(f"[Social] Failed: {e}")
        return {"social_data": {"status": "error", "error": str(e)}}