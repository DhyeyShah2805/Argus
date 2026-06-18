"""
FastAPI Backend
"""
from dotenv import load_dotenv
load_dotenv()

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.agents.graph import run_research
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AI Trading Research Agent", version="1.0.0")

# ── Rate limiting ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    ticker: str
    context: str = "long-term investor"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/research")
@limiter.limit("5/minute")
@limiter.limit("30/hour")
async def research(request: Request, body: ResearchRequest):
    if not body.ticker.strip():
        raise HTTPException(status_code=400, detail="Ticker required")

    try:
        state = await run_research(body.ticker, body.context)
        return {
            "ticker": body.ticker.upper(),
            "report": state["final_report"],
            "metadata": state["report_metadata"],
            "thesis": state["thesis"],
            "risk_critique": state["risk_critique"],
            "financials": state["financials_data"],
            "news_summary": {
                "avg_sentiment": state.get("news_data", {}).get("avg_sentiment"),
                "article_count": state.get("news_data", {}).get("article_count"),
            },
            "social_summary": {
                "avg_sentiment": state.get("social_data", {}).get("avg_sentiment"),
                "mention_count": state.get("social_data", {}).get("mention_count"),
            },
            "insider_signal": state.get("insider_data", {}).get("signal"),
            "peers": state.get("competitor_data", {}).get("peers", []),
            "peer_avg_pe": state.get("competitor_data", {}).get("avg_peer_pe"),
            "earnings": state.get("earnings_data", {}).get("recent_earnings", []),
            "insider_detail": {
                "buy_count": state.get("insider_data", {}).get("buy_count"),
                "sell_count": state.get("insider_data", {}).get("sell_count"),
                "shares_bought": state.get("insider_data", {}).get("shares_bought"),
                "shares_sold": state.get("insider_data", {}).get("shares_sold"),
            },
        }
    except Exception as e:
        logging.error(f"Research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))