# AI Trading Research Agent

Multi-agent system that takes a ticker (or sector) and autonomously produces an institutional-quality research report — pulling SEC filings, financials, news, social sentiment, earnings calls, and insider trading data in parallel.

> Not a trading bot. A research analyst.

## What It Does

**Input:** `AAPL` or `semiconductor sector outlook 2026`

**Output:** Structured 5–10 page research report:
- Investment thesis (bull/bear case)
- Financial health summary
- Competitive positioning
- Earnings call sentiment
- News + social sentiment
- Insider trading activity
- Risk factors
- Final recommendation with confidence score

## Architecture

```
User Query (ticker / sector)
    ↓
[Orchestrator]    → builds research plan, dispatches sub-agents
    ↓
    ├─ [Filings Agent]      → SEC EDGAR (10-K, 10-Q, 8-K)
    ├─ [Financials Agent]   → yfinance ratios + trends
    ├─ [News Agent]         → Tavily + NewsAPI + FinBERT sentiment
    ├─ [Social Agent]       → Reddit (WSB, investing) sentiment
    ├─ [Earnings Agent]     → Transcripts + tone analysis
    ├─ [Insider Agent]      → Form 4 filings, exec activity
    └─ [Competitor Agent]   → Peer benchmark, market share
    ↓  (all in parallel)
[Synthesis Agent]   → builds investment thesis
    ↓
[Risk Agent]        → adversarial critique, blind-spot detection
    ↓
[Report Writer]     → final structured report with charts
```

## Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph (parallel branches) |
| LLM | Ollama (local) / Claude API |
| SEC Filings | sec-edgar-downloader |
| Market Data | yfinance |
| News | Tavily, NewsAPI |
| Social | PRAW (Reddit) |
| Sentiment | FinBERT (financial-domain BERT) |
| Vector DB | Qdrant (filing chunks cached) |
| Backend | FastAPI |
| Frontend | Streamlit + Plotly |

## Quickstart

```bash
# 1. Install deps (no GPU needed for dev)
pip install -r requirements.txt

# 2. Set up env
cp .env.example .env  # add API keys

# 3. Start Qdrant
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant

# 4. Start Ollama (if not running)
ollama pull mistral
ollama serve

# 5. Smoke test
python test_connections.py

# 6. Run backend + frontend
uvicorn backend.api.main:app --reload &
streamlit run frontend/app.py
```

## 20-Day Plan

| Days | Milestone |
|---|---|
| 1–2 | Env, smoke tests, SEC/yfinance/NewsAPI/Reddit keys |
| 3–4 | Filings Agent (EDGAR, chunking, vector cache) |
| 5–6 | Financials Agent (yfinance ratios) |
| 7–8 | News + Social agents with FinBERT |
| 9 | Earnings call agent |
| 10 | Insider trading (Form 4) agent |
| 11–12 | Competitor agent + peer benchmarking |
| 13–14 | Orchestrator with parallel LangGraph branches |
| 15 | Synthesis agent — thesis building |
| 16 | Risk agent — adversarial critique loop |
| 17 | Report writer + chart embedding |
| 18 | Streamlit UI |
| 19 | Backtest eval on 10 tickers |
| 20 | Demo video + launch |

## Disclaimer

This tool produces educational research, not investment advice. Always consult a licensed financial advisor before making investment decisions.

## Backtest Results

**75% directional accuracy** across 20 tickers / 4 sectors (30-day forward window).

| Sector | Accuracy |
|--------|----------|
| Finance | 100% (5/5) |
| Healthcare | 100% (5/5) |
| Consumer | 60% (3/5) |
| Tech | 40% (2/5) |
