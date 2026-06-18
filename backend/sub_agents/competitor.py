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
    """
    Peer discovery with curated overrides.

    Free peer APIs (Finnhub) return unreliable results for major tickers —
    e.g. AAPL returns storage/hardware names, not its real comps. For liquid
    large-caps we use analyst-consensus peer groups; everything else falls
    back to Finnhub's automated list, then a sector pool as last resort.
    """
    ticker = ticker.upper()

    # 1. Curated peer groups for major names (free APIs unreliable here)
    CURATED = {
        "AAPL": ["MSFT", "GOOGL", "META", "NVDA", "AMZN"],
        "MSFT": ["AAPL", "GOOGL", "AMZN", "ORCL", "CRM"],
        "GOOGL": ["META", "MSFT", "AAPL", "AMZN", "NFLX"],
        "META": ["GOOGL", "SNAP", "PINS", "MSFT", "NFLX"],
        "NVDA": ["AMD", "AVGO", "INTC", "QCOM", "TSM"],
        "AMZN": ["MSFT", "GOOGL", "WMT", "SHOP", "EBAY"],
        "TSLA": ["F", "GM", "RIVN", "LCID", "NIO"],
        "JPM": ["BAC", "WFC", "C", "GS", "MS"],
        "BAC": ["JPM", "WFC", "C", "GS", "MS"],
        "JNJ": ["PFE", "MRK", "ABBV", "LLY", "BMY"],
        "PFE": ["JNJ", "MRK", "ABBV", "LLY", "BMY"],
        "BA": ["LMT", "RTX", "GD", "NOC", "GE"],
    }
    if ticker in CURATED:
        logger.info(f"[Competitor] {ticker}: curated peer group")
        return CURATED[ticker]

    # 2. Finnhub for everything else (automated long tail)
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            fh = finnhub.Client(api_key=finnhub_key)
            peers = [p for p in fh.company_peers(ticker) if p != ticker]
            if peers:
                logger.info(f"[Competitor] {ticker}: Finnhub peers")
                return peers[:6]
        except Exception as e:
            logger.warning(f"[Competitor] Finnhub failed: {e}")

    # 3. Last resort — curated sector pool by yfinance sector
    try:
        sector = yf.Ticker(ticker).info.get("sector", "")
        SECTOR_PEERS = {
            "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "AVGO"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "TMUS"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "MCD"],
            "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS"],
            "Healthcare": ["JNJ", "PFE", "UNH", "ABBV", "MRK"],
            "Industrials": ["BA", "LMT", "RTX", "GD", "HON"],
        }
        pool = [p for p in SECTOR_PEERS.get(sector, []) if p != ticker]
        if pool:
            logger.info(f"[Competitor] {ticker}: sector pool ({sector})")
            return pool[:5]
    except Exception:
        pass

    return []