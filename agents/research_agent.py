"""
agents/research_agent.py
------------------------
Research Agent

Flow

User
 ↓
Tavily Search
 ↓
LLM Summary
 ↓
Author Agent
"""

import asyncio
import logging
import time
import os
from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.search_tools import tavily_search
from tools.llm import get_llm

logger = logging.getLogger(__name__)


_SYNTHESIS_PROMPT = """
You are a research assistant.

Answer the user's question ONLY using the web sources below.

Guidelines:

- Prefer the latest information.
- Be concise.
- Cite sources inline as [1], [2], etc.
- If information is unavailable, say so.

Sources:

{sources}

Question:

{question}

Answer:
"""


async def research_agent_node(state: AgentState):

    start = time.time()

    emit = state.get("emit")

    query = state["user_query"]

    # ----------------------------------------------------------
    # Search
    # ----------------------------------------------------------

    if emit:
        await emit(
            "agent_progress",
            "research",
            "Searching the web..."
        )

    tavily_result = await asyncio.to_thread(
        tavily_search,
        query
    )

    search_results = tavily_result.get("results", [])

    if not search_results:

        return {

            "research_output": {},

            "agent_result": {
                "agent": "research",
                "content": "No relevant web results found.",
                "sources": [],
                "raw": tavily_result,
            },

            "latency_ms": {
                **state.get("latency_ms", {}),
                "research": int((time.time() - start) * 1000),
            },
        }

    # ----------------------------------------------------------
    # Build source context
    # ----------------------------------------------------------

    sources_block = ""

    source_urls = []

    for index, result in enumerate(search_results, start=1):

        source_urls.append(result["url"])

        sources_block += f"""
[{index}]

Title:
{result.get("title","")}

URL:
{result.get("url","")}

Content:
{result.get("content","")}
"""

    # ----------------------------------------------------------
    # LLM Synthesis
    # ----------------------------------------------------------

    if emit:
        await emit(
            "agent_progress",
            "research",
            "Generating final answer..."
        )

    prompt = ChatPromptTemplate.from_template(
        _SYNTHESIS_PROMPT
    )

    chain = prompt | get_llm()

    response = await asyncio.to_thread(

        chain.invoke,

        {

            "sources": sources_block,

            "question": query,

        }

    )

    latency = int((time.time() - start) * 1000)

    return {

        "research_output": tavily_result,

        "agent_result": {

            "agent": "research",

            "content": response.content,

            "sources": source_urls,

            "raw": tavily_result,

        },

        "latency_ms": {

            **state.get("latency_ms", {}),

            "research": latency,

        }

    }