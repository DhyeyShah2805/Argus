"""
Streamlit Frontend
"""

import os
import streamlit as st
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Trading Research Agent",
    page_icon="📈",
    layout="wide",
)

st.title("📈 AI Trading Research Agent")
st.caption("Multi-agent equity research — 7 sub-agents working in parallel")

with st.sidebar:
    st.header("⚙️ Pipeline")
    st.markdown("""
    1. 🎯 **Orchestrator** plans the research
    2. 🔍 **Sub-agents** (parallel):
       - Filings (SEC EDGAR)
       - Financials (yfinance)
       - News (Tavily + FinBERT)
       - Social (Reddit + FinBERT)
       - Earnings
       - Insider trading
       - Competitors
    3. 🧠 **Synthesis** builds thesis
    4. ⚠️ **Risk** agent critiques
    5. ✍️ **Writer** produces report
    """)
    st.warning("⚠️ Educational research only. Not investment advice.")

# ─── Input ────────────────────────────────────────────────────────
col_in1, col_in2 = st.columns([3, 1])
with col_in1:
    ticker = st.text_input(
        "Ticker",
        placeholder="AAPL, NVDA, TSLA, etc.",
        max_chars=10,
    ).upper().strip()
with col_in2:
    context = st.selectbox(
        "Investor type",
        ["long-term investor", "short-term trader", "value investor", "growth investor"],
    )

run_button = st.button("🔬 Run Research", type="primary", use_container_width=True)

# ─── Stock price chart (always show if ticker entered) ────────────
if ticker:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if len(hist) > 0:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"],
                name=ticker,
            ))
            fig.update_layout(
                title=f"{ticker} — 1Y Price",
                xaxis_rangeslider_visible=False,
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info(f"Could not load price chart for {ticker}")

# ─── Run Research ─────────────────────────────────────────────────
if run_button and ticker:
    with st.spinner(f"7 agents researching {ticker} in parallel... (~1-2 min)"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/research",
                json={"ticker": ticker, "context": context},
                timeout=600,
            )
            response.raise_for_status()
            result = response.json()

            st.success(f"✅ Research complete for {ticker}")

            # Top-line recommendation
            thesis = result.get("thesis", {})
            rec = thesis.get("recommendation", "—")
            conf = thesis.get("confidence", 0)

            rec_color = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}.get(rec, "⚪")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Recommendation", f"{rec_color} {rec}")
            r2.metric("Confidence", f"{conf}%")
            r3.metric("News Sentiment", result.get("news_summary", {}).get("avg_sentiment", "—"))
            r4.metric("Insider Signal", result.get("insider_signal", "—"))

            st.markdown("---")

            # Full report
            st.markdown(result["report"])

            # Detail expanders
            with st.expander("📊 Raw Financial Data"):
                st.json(result.get("financials", {}))
            with st.expander("⚠️ Risk Critique"):
                st.json(result.get("risk_critique", {}))
            with st.expander("📋 Report Metadata"):
                st.json(result.get("metadata", {}))

            # Download
            st.download_button(
                "⬇️ Download Report (Markdown)",
                data=result["report"],
                file_name=f"{ticker}_research_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )

        except requests.exceptions.ConnectionError:
            st.error("❌ Backend not running. Start with: `uvicorn backend.api.main:app --reload`")
        except Exception as e:
            st.error(f"❌ {str(e)}")

elif run_button:
    st.warning("Enter a ticker first.")
