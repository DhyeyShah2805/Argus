"""
Competitor Sub-Agent
--------------------
Identifies industry peers via yfinance / Finnhub,
pulls comparable financials, computes relative valuation.
"""

import os
import logging
import yfinance as yf
import finnhub
from backend.agents.state import ResearchState

logger = logging.getLogger(__name__)


def competitor_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"competitor_data": {"status": "skipped"}}

    logger.info(f"[Competitor] Finding peers for {ticker}")

    try:
        peers = _get_peers(ticker)
        if not peers:
            return {"competitor_data": {"status": "no peers found"}}

        # Pull comparable metrics for each peer
        peer_metrics = []
        for peer_ticker in peers[:6]:   # cap at 6 to limit API calls
            try:
                info = yf.Ticker(peer_ticker).info
                peer_metrics.append({
                    "ticker": peer_ticker,
                    "name": info.get("shortName", peer_ticker),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "ps_ratio": info.get("priceToSalesTrailing12Months"),
                    "profit_margin": info.get("profitMargins"),
                    "revenue_growth": info.get("revenueGrowth"),
                })
            except Exception as e:
                logger.warning(f"[Competitor] Failed for {peer_ticker}: {e}")

        # Compute averages for context
        valid_pes = [p["pe_ratio"] for p in peer_metrics if p["pe_ratio"]]
        valid_margins = [p["profit_margin"] for p in peer_metrics if p["profit_margin"]]

        avg_peer_pe = sum(valid_pes) / len(valid_pes) if valid_pes else None
        avg_peer_margin = sum(valid_margins) / len(valid_margins) if valid_margins else None

        return {
            "competitor_data": {
                "peers": peer_metrics,
                "peer_count": len(peer_metrics),
                "avg_peer_pe": round(avg_peer_pe, 2) if avg_peer_pe else None,
                "avg_peer_margin": round(avg_peer_margin, 4) if avg_peer_margin else None,
                "source": "yfinance + Finnhub peers",
            }
        }

    except Exception as e:
        logger.error(f"[Competitor] Failed: {e}")
        return {"competitor_data": {"status": "error", "error": str(e)}}


def _get_peers(ticker: str) -> list:
    """Try Finnhub for peer list, else fallback to hand-coded sector peers."""
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            fh = finnhub.Client(api_key=finnhub_key)
            peers = fh.company_peers(ticker)
            return [p for p in peers if p != ticker][:8]
        except Exception as e:
            logger.warning(f"[Competitor] Finnhub peers failed: {e}")

    # Fallback: use yfinance sector info to build minimal peer set
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")
        # Hardcoded mini peer map for common sectors
        SECTOR_PEERS = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "T"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "SBUX"],
            "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS"],
            "Healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
        }
        peers = SECTOR_PEERS.get(sector, [])
        return [p for p in peers if p != ticker][:5]
    except Exception:
        return []
