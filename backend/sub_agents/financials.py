"""
Financials Sub-Agent
--------------------
Pulls fundamental data via yfinance:
- Valuation ratios (P/E, P/B, P/S, EV/EBITDA)
- Profitability (ROE, ROA, gross/net margin)
- Growth (revenue/EPS YoY, QoQ)
- Balance sheet health (current ratio, debt/equity)
- Cash flow trends
"""

import logging
import yfinance as yf
from backend.agents.state import ResearchState

logger = logging.getLogger(__name__)


def financials_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]
    if not ticker:
        return {"financials_data": {"status": "skipped"}}

    logger.info(f"[Financials] Fetching for {ticker}")

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Pull recent price history
        history = stock.history(period="1y")
        price_change_1y = (
            (history["Close"].iloc[-1] / history["Close"].iloc[0] - 1) * 100
            if len(history) > 0 else None
        )

        ratios = {
            "P/E (trailing)": info.get("trailingPE"),
            "P/E (forward)": info.get("forwardPE"),
            "P/B": info.get("priceToBook"),
            "P/S": info.get("priceToSalesTrailing12Months"),
            "EV/EBITDA": info.get("enterpriseToEbitda"),
            "Profit Margin": info.get("profitMargins"),
            "ROE": info.get("returnOnEquity"),
            "ROA": info.get("returnOnAssets"),
            "Debt/Equity": info.get("debtToEquity"),
            "Current Ratio": info.get("currentRatio"),
            "Revenue Growth (YoY)": info.get("revenueGrowth"),
            "Earnings Growth (YoY)": info.get("earningsGrowth"),
        }

        # Clean Nones for display
        ratios_clean = {k: v for k, v in ratios.items() if v is not None}

        return {
            "financials_data": {
                "company_name": info.get("longName", ticker),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "current_price": info.get("currentPrice"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "price_change_1y_pct": round(price_change_1y, 2) if price_change_1y else None,
                "ratios": ratios_clean,
                "analyst_target": info.get("targetMeanPrice"),
                "analyst_recommendation": info.get("recommendationKey"),
                "source": "yfinance",
            }
        }

    except Exception as e:
        logger.error(f"[Financials] Failed: {e}")
        return {"financials_data": {"status": "error", "error": str(e)}}
