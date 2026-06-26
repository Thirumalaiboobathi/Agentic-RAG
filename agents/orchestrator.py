"""
agents/orchestrator.py
----------------------
Orchestrator — decides which agent handles the user query.

Routing strategy (hybrid: fast rules + LLM fallback):
  1. Org match     → if the query mentions a known organization → Knowledge Brain
  2. SQL keywords  → if the query has data-question keywords     → SQL Agent
  3. LLM decision  → ambiguous cases → ask the LLM to classify
  4. Default       → Research Agent

The rule-based checks run first because they're instant and free. The LLM
is only consulted when rules don't give a confident answer.
"""

import logging
import re
from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from config.settings import settings
from tools.llm import get_llm

logger = logging.getLogger(__name__)

_ORG_ALIASES = settings.all_org_aliases()
_SQL_KEYWORDS = [k.lower() for k in settings.routing["sql_keywords"]]


_BMI_KEYWORDS = [
    "bmi",
    "body mass index",
    "height",
    "weight",
    "obesity",
    "ideal weight"
]

_DRUG_KEYWORDS = [
    "drug",
    "medicine",
    "tablet",
    "capsule",
    "paracetamol",
    "ibuprofen",
    "aspirin",
    "dosage",
    "side effect",
    "interaction"
]


_CLASSIFY_PROMPT = """
Classify the user's question into exactly ONE category.

- knowledge
- sql
- weather
- bmi
- drug
- research

Definitions:

knowledge:
Questions about internal documents, policies, SOPs and medical knowledge.

sql:
Questions asking for counts, totals or database information.

weather:
Current weather, forecast, rain, humidity, temperature.

bmi:
Questions asking to calculate BMI, body mass index, ideal weight, or containing both height and weight.

drug:
Questions about medicines, dosage, side effects, interactions, warnings, tablets or capsules.

research:
Everything else.

Respond with ONLY one word:

knowledge
sql
weather
bmi
drug
research

Question:
{question}

Category:
"""

def _check_org_match(query: str) -> str | None:
    """Return canonical org name if any alias appears in the query, else None."""
    q_lower = query.lower()
    for alias, canonical in _ORG_ALIASES.items():
        # Word-boundary-ish check to avoid false hits on short aliases
        if alias in q_lower:
            return canonical
    return None


def _check_sql_keywords(query: str) -> bool:
    """Return True if the query contains data-question keywords."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in _SQL_KEYWORDS)



def _check_bmi(query: str):

    q = query.lower()

    if any(k in q for k in [
        "bmi",
        "body mass index",
        "calculate bmi",
        "ideal weight",
    ]):
        return True

    has_height = re.search(r"\d+(\.\d+)?\s*cm", q)
    has_weight = re.search(r"\d+(\.\d+)?\s*kg", q)

    return bool(has_height and has_weight)


def _check_drug(query):
    q = query.lower()
    
    keywords = [
        "drug",
        "medicine",
        "tablet",
        "capsule",
        "dosage",
        "dose",
        "side effect",
        "interaction",
        "contraindication",
        "uses",
        "warnings",
    ]

    return any(k in q for k in keywords)


async def orchestrator_node(state: AgentState) -> dict:
    """
    LangGraph node — routing decision. Sets selected_agent in state.
    """
    emit = state.get("emit")
    query = state["user_query"]

    # ── Rule 1: Organization match → Knowledge Brain ─────────────────────────
    org = _check_org_match(query)
    if org:
        if emit:
            await emit("agent_selected", "knowledge",
                       f"Routing to Knowledge Brain ({org} data)")
        return {
            "selected_agent": "knowledge",
            "routing_reason": f"Query mentions organization '{org}'",
            "detected_org": org,
        }

    # ── Rule 2: SQL keywords → SQL Agent ──────────────────────────────────────
    if _check_sql_keywords(query):
        if emit:
            await emit("agent_selected", "sql", "Routing to SQL Agent (data question)")
        return {
            "selected_agent": "sql",
            "routing_reason": "Query contains data-question keywords",
            "detected_org": None,
        }
    if _check_bmi(query):

        if emit:
            await emit(
                "agent_selected",
                "bmi",
                "Routing to BMI Agent"
            )

        return {
            "selected_agent": "bmi",
            "routing_reason": "BMI calculation request",
            "detected_org": None,
    }
    # ── Rule 5: Drug → Drug Agent ──────────────────────────────────────
    if _check_drug(query):

        if emit:
            await emit(
                "agent_selected",
                "drug",
                "Routing to Drug Information Agent"
            )

        return {
            "selected_agent": "drug",
            "routing_reason": "Drug information request",
            "detected_org": None,
    }

    
        

    # ── Rule 3: LLM classification for ambiguous cases ────────────────────────
    prompt = ChatPromptTemplate.from_template(_CLASSIFY_PROMPT)
    chain = prompt | get_llm()
    decision = chain.invoke({"question": query}).content.strip().lower()

    # Normalise the LLM answer to a valid agent name
    if "knowledge" in decision:
        selected = "knowledge"
    elif "sql" in decision:
        selected = "sql"
    
    elif "bmi" in decision:
        selected = "bmi"

    elif "drug" in decision:
        selected = "drug"

    else:
        selected = "research"   # default fallback

    if emit:
        await emit("agent_selected", selected, f"Routing to {selected} agent")

    logger.info(f"Orchestrator routed to '{selected}' (LLM decision: '{decision}')")
    return {
        "selected_agent": selected,
        "routing_reason": f"LLM classified query as '{selected}'",
        "detected_org": None,
    }


def route_decision(state: AgentState) -> str:
    """
    Conditional edge function — returns the next node name based on
    selected_agent. Used by the graph's add_conditional_edges.
    """
    if state.get("guardrail_blocked"):
        return "blocked"
    return state.get("selected_agent", "research")
