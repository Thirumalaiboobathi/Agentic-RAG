import asyncio
import logging
import re
import time

from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.drug_tool import get_drug_information
from tools.llm import get_llm

logger = logging.getLogger(__name__)

_DRUG_PROMPT = """
You are a professional Drug Information Assistant.

Using ONLY the official drug information below, answer the user's question.

Drug Information:
{drug_data}

User Question:
{question}

Provide:

- Drug Name
- Purpose / Uses
- Recommended Dosage
- Important Warnings
- Common Side Effects
- Precautions

If any field is unavailable, say "Information not available."
"""


async def drug_agent_node(state: AgentState):

    start = time.time()

    emit = state.get("emit")
    query = state["user_query"]

    # Simple drug extraction
    match = re.search(
        r"(?:about|of|for)?\s*([A-Za-z0-9\s\-]+)$",
        query.strip()
    )

    if match:
        drug_name = match.group(1).strip()
    else:
        return {
            "agent_result": {
                "agent": "drug",
                "content": "Please mention a drug name.\n\nExample:\nTell me about Paracetamol",
                "sources": [],
                "raw": {}
            }
        }

    if emit:
        await emit(
            "agent_progress",
            "drug",
            f"Fetching drug information for {drug_name}..."
        )

    try:

        drug = await asyncio.to_thread(
            get_drug_information,
            drug_name
        )

    except Exception as e:

        logger.exception(e)

        return {
            "agent_result": {
                "agent": "drug",
                "content": "Unable to retrieve drug information.",
                "sources": [],
                "raw": {"error": str(e)}
            }
        }

    if "error" in drug:

        return {
            "agent_result": {
                "agent": "drug",
                "content": drug["error"],
                "sources": [],
                "raw": drug
            }
        }

    if emit:
        await emit(
            "agent_progress",
            "drug",
            "Generating response..."
        )

    prompt = ChatPromptTemplate.from_template(_DRUG_PROMPT)

    chain = prompt | get_llm()

    response = await asyncio.to_thread(
        chain.invoke,
        {
            "drug_data": drug,
            "question": query
        }
    )

    latency = int((time.time() - start) * 1000)

    return {
        "drug_output": drug,
        "agent_result": {
            "agent": "drug",
            "content": response.content,
            "sources": ["OpenFDA"],
            "raw": drug
        },
        "latency_ms": {
            **state.get("latency_ms", {}),
            "drug": latency,
        }
    }