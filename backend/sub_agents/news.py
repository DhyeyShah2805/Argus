"""
News Sub-Agent
--------------
Pulls recent news via Tavily + NewsAPI,
scores sentiment using FinBERT (financial-domain BERT),
and extracts key themes.
"""

import os
import logging
from datetime import datetime, timedelta
from tavily import TavilyClient
from backend.agents.state import ResearchState
from backend.ml.finbert import score_sentiment

logger = logging.getLogger(__name__)
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))


def news_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    target = state.get("financials_data", {}).get("company_name") or ticker
    logger.info(f"[News] Pulling news for {target}")

    try:
        # Tavily search for recent news
        results = tavily.search(
            query=f"{target} stock news earnings",
            search_depth="advanced",
            max_results=10,
            days=30,
        )
        articles = results.get("results", [])

        # Score sentiment on each article title + content
        scored = []
        for article in articles:
            text = f"{article.get('title', '')}. {article.get('content', '')[:500]}"
            sentiment = score_sentiment(text)
            scored.append({
                "title": article.get("title"),
                "url": article.get("url"),
                "snippet": article.get("content", "")[:300],
                "sentiment": sentiment["label"],
                "sentiment_score": sentiment["score"],
                "published": article.get("published_date"),
            })

        # Aggregate
        if scored:
            avg_score = sum(s["sentiment_score"] for s in scored) / len(scored)
            pos = sum(1 for s in scored if s["sentiment"] == "positive")
            neg = sum(1 for s in scored if s["sentiment"] == "negative")
        else:
            avg_score, pos, neg = 0, 0, 0

        return {
            "news_data": {
                "article_count": len(scored),
                "articles": scored[:8],
                "avg_sentiment": round(avg_score, 3),
                "positive_count": pos,
                "negative_count": neg,
                "neutral_count": len(scored) - pos - neg,
                "source": "Tavily + FinBERT",
            }
        }

    except Exception as e:
        logger.error(f"[News] Failed: {e}")
        return {"news_data": {"status": "error", "error": str(e)}}
