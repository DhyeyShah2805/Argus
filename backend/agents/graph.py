"""
Research Agent Graph (LangGraph)
--------------------------------
Orchestrator → 7 sub-agents in PARALLEL → Synthesis → Risk → (loop if needed) → Writer

This is the magic — all sub-agents run concurrently using
LangGraph's parallel branching.
"""

import os
import logging
from langgraph.graph import StateGraph, END
from backend.agents.state import ResearchState
from backend.agents.orchestrator import orchestrator_agent
from backend.agents.synthesis import synthesis_agent
from backend.agents.risk import risk_agent
from backend.agents.writer import report_writer

from backend.sub_agents.filings import filings_agent
from backend.sub_agents.financials import financials_agent
from backend.sub_agents.news import news_agent
from backend.sub_agents.earnings import earnings_agent
from backend.sub_agents.insider import insider_agent
from backend.sub_agents.competitor import competitor_agent
from backend.agents.calibrator import calibrator_agent

logger = logging.getLogger(__name__)
MAX_ITERATIONS = int(os.getenv("MAX_CRITIQUE_ITERATIONS", 2))


def should_loop(state: ResearchState) -> str:
    """After risk critique: write report OR loop back for more research."""
    if state["critique_passed"] or state["iteration"] >= MAX_ITERATIONS:
        return "writer"
    logger.info(f"[Graph] Risk critique failed, looping back (iter {state['iteration']})")
    return "synthesis"   # re-synthesize with critique in mind


def build_graph():
    graph = StateGraph(ResearchState)

    # Top-level agents
    graph.add_node("orchestrator", orchestrator_agent)
    graph.add_node("synthesis", synthesis_agent)
    graph.add_node("calibrator", calibrator_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("writer", report_writer)

    # Sub-agents (will run in parallel)
    graph.add_node("filings", filings_agent)
    graph.add_node("financials", financials_agent)
    graph.add_node("news", news_agent)
    graph.add_node("earnings", earnings_agent)
    graph.add_node("insider", insider_agent)
    graph.add_node("competitor", competitor_agent)

    # Flow
    graph.set_entry_point("orchestrator")

    # Fan out — orchestrator → all 7 sub-agents in parallel
    for sub in ["filings", "financials", "news",
                "earnings", "insider", "competitor"]:
        graph.add_edge("orchestrator", sub)
        graph.add_edge(sub, "synthesis")   # all converge to synthesis

    # Synthesis → Risk → conditional → Writer or loop
    # Synthesis → Calibrator → Risk → conditional → Writer or loop
    graph.add_edge("synthesis", "calibrator")
    graph.add_edge("calibrator", "risk")
    graph.add_conditional_edges(
        "risk",
        should_loop,
        {"writer": "writer", "synthesis": "synthesis"}
    )
    graph.add_edge("writer", END)

    return graph.compile()


research_graph = build_graph()


async def run_research(ticker: str, context: str = "long-term investor") -> dict:
    logger.info(f"[Graph] Starting research for {ticker}")

    initial_state: ResearchState = {
        "ticker": ticker.upper(),
        "sector": None,
        "query_context": context,
        "research_plan": "",
        "sub_agents_to_run": [],
        "filings_data": {},
        "financials_data": {},
        "news_data": {},
        "social_data": {},
        "earnings_data": {},
        "insider_data": {},
        "competitor_data": {},
        "thesis": {},
        "risk_critique": {},
        "critique_passed": False,
        "final_report": "",
        "report_metadata": {},
        "iteration": 0,
        "max_iterations": MAX_ITERATIONS,
    }

    final_state = await research_graph.ainvoke(initial_state)
    logger.info(f"[Graph] Research complete for {ticker}")
    return final_state
