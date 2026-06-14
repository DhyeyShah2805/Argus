"""
Streamlit Frontend
"""

import os
import streamlit as st
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path


def render_backtest_panel():
    metrics_path = Path("data/reports/backtest_metrics.json")
    if not metrics_path.exists():
        st.info("No backtest results yet. Run `python -m scripts.backtest_eval` to generate them.")
        return

    metrics = json.loads(metrics_path.read_text())

    # Headline metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Accuracy", f"{metrics['overall_accuracy_pct']}%")
    c2.metric("Tickers Scored", metrics["tickers_scored"])
    rec_dist = metrics.get("recommendation_distribution", {})
    dist_str = " / ".join(f"{k}:{v}" for k, v in rec_dist.items())
    c3.metric("Rec Distribution", dist_str)

    # Accuracy by sector — bar chart
    by_sector = metrics.get("by_sector", {})
    if by_sector:
        sectors = list(by_sector.keys())
        accuracies = [by_sector[s]["accuracy_pct"] for s in sectors]
        counts = [by_sector[s]["n"] for s in sectors]

        fig = go.Figure(data=[
            go.Bar(
                x=sectors,
                y=accuracies,
                text=[f"{a}%<br>(n={n})" for a, n in zip(accuracies, counts)],
                textposition="auto",
                marker_color=["#2563eb", "#16a34a", "#dc2626", "#ea580c"][:len(sectors)],
            )
        ])
        fig.add_hline(
            y=50, line_dash="dash", line_color="gray",
            annotation_text="coin-flip baseline (50%)",
            annotation_position="top right",
        )
        fig.update_layout(
            title="Directional Accuracy by Sector",
            yaxis_title="Accuracy (%)",
            yaxis_range=[0, 105],
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Confidence band breakdown
    by_conf = metrics.get("by_confidence", {})
    if by_conf:
        st.markdown("**Accuracy by Confidence Band**")
        for band, m in by_conf.items():
            st.write(f"- {band}: {m['accuracy_pct']}% (n={m['n']})")

    st.caption(
        "⚠️ Scoring uses a rolling 30-day forward window from the current date, "
        "so results shift with market conditions. The system shows a BUY bias "
        "corrected by a rule-based calibration layer. See BACKTEST_RESULTS.md for full analysis."
    )
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
# ─── Backtest Performance ────────────────────────────────────────
st.markdown("---")
with st.expander("📊 View Backtest Performance", expanded=False):
    render_backtest_panel()