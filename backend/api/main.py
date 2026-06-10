"""
FastAPI Backend
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.agents.graph import run_research

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AI Trading Research Agent", version="1.0.0")

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
async def research(request: ResearchRequest):
    if not request.ticker.strip():
        raise HTTPException(status_code=400, detail="Ticker required")

    try:
        state = await run_research(request.ticker, request.context)
        return {
            "ticker": request.ticker.upper(),
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
        }
    except Exception as e:
        logging.error(f"Research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
