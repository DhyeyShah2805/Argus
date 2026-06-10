"""
Social Sub-Agent
----------------
Scrapes Reddit (r/wallstreetbets, r/investing, r/stocks)
for ticker mentions in the last week.
Scores aggregate sentiment + mention volume.
"""

import os
import logging
import praw
from datetime import datetime, timedelta
from backend.agents.state import ResearchState
from backend.ml.finbert import batch_score

logger = logging.getLogger(__name__)

SUBREDDITS = ["wallstreetbets", "investing", "stocks", "SecurityAnalysis"]


def _get_reddit():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        user_agent=os.getenv("REDDIT_USER_AGENT", "trading-research-agent"),
    )


def social_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"social_data": {"status": "skipped"}}

    logger.info(f"[Social] Searching Reddit for {ticker}")

    try:
        reddit = _get_reddit()
        all_posts = []

        for sub_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(sub_name)
                for submission in subreddit.search(ticker, time_filter="week", limit=10):
                    all_posts.append({
                        "title": submission.title,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "subreddit": sub_name,
                        "url": f"https://reddit.com{submission.permalink}",
                        "created": datetime.fromtimestamp(submission.created_utc).isoformat(),
                        "text": submission.selftext[:500] if submission.selftext else "",
                    })
            except Exception as e:
                logger.warning(f"[Social] Subreddit {sub_name} failed: {e}")

        if not all_posts:
            return {"social_data": {"mention_count": 0, "status": "no posts found"}}

        # Sentiment via FinBERT (batch)
        texts = [f"{p['title']}. {p['text']}" for p in all_posts]
        sentiments = batch_score(texts)
        for post, sent in zip(all_posts, sentiments):
            post["sentiment"] = sent["label"]
            post["sentiment_score"] = sent["score"]

        avg_sentiment = sum(s["score"] for s in sentiments) / len(sentiments)
        total_engagement = sum(p["score"] + p["num_comments"] for p in all_posts)

        # Top posts by engagement
        top_posts = sorted(
            all_posts, key=lambda p: p["score"] + p["num_comments"], reverse=True
        )[:5]

        return {
            "social_data": {
                "mention_count": len(all_posts),
                "avg_sentiment": round(avg_sentiment, 3),
                "total_engagement": total_engagement,
                "top_posts": top_posts,
                "subreddits_searched": SUBREDDITS,
                "source": "Reddit + FinBERT",
            }
        }

    except Exception as e:
        logger.error(f"[Social] Failed: {e}")
        return {"social_data": {"status": "error", "error": str(e)}}
