"""
Orchestrator Agent
------------------
Inspects the query and dispatches sub-agents in parallel.
For now we always run all of them — later, can be smarter
about skipping (e.g. skip insider for a sector query).
"""

import logging
import json
from backend.agents.state import ResearchState
from backend.utils.llm import get_llm

logger = logging.getLogger(__name__)

ORCHESTRATOR_PROMPT = """You are a senior equity research director.

Build a research plan for analyzing this ticker/sector.

Target: {target}
Context: {context}

Write a 3-4 sentence plan describing what angles matter most
for this specific stock/sector.

Return ONLY valid JSON:
{{
  "research_plan": "<the plan>",
  "key_focus_areas": ["area 1", "area 2", "area 3"]
}}
"""


def orchestrator_agent(state: ResearchState) -> dict:
    target = state["ticker"] or state.get("sector", "")
    context = state.get("query_context", "general long-term investor")
    logger.info(f"[Orchestrator] Planning research for: {target}")

    llm = get_llm(json_mode=True)
    prompt = ORCHESTRATOR_PROMPT.format(target=target, context=context)

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        clean = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        plan = result["research_plan"]
    except Exception as e:
        logger.warning(f"[Orchestrator] Failed to parse: {e}")
        plan = f"Standard equity research on {target}: financials, filings, news, sentiment, competitive landscape."

    return {
        "research_plan": plan,
        "sub_agents_to_run": [
            "filings", "financials", "news",
            "social", "earnings", "insider", "competitor"
        ],
        "iteration": 0,
    }
