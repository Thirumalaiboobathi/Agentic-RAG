"""
agents/research_agent.py
------------------------
Research Agent — handles anything that isn't internal org data or a SQL
data question. The default fallback route.

Flow:
  1. google_search(query)        — get top URLs
  2. read_url(url) for each      — fetch latest content (up to max_urls_to_read)
  3. LLM synthesis               — combine into an answer with citations

Emits progress for each phase, including per-URL reading so the Angular
client can show "Reading source 1 of 3...".
"""

import asyncio
import time
import logging

from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.search_tools import google_search, read_url
from tools.llm import get_llm
from config.settings import settings

logger = logging.getLogger(__name__)


_SYNTHESIS_PROMPT = """You are a research assistant. Answer the user's question using the
web sources below. Cite sources inline as [1], [2], etc. matching the source numbers.
Prefer the most recent and authoritative information. Be concise.

Sources:
{sources}

Question: {question}

Answer:"""


async def research_agent_node(state: AgentState) -> dict:
    """
    LangGraph node for the Research agent.
    """
    start = time.time()
    emit = state.get("emit")
    query = state["user_query"]
    max_urls = settings.research["max_urls_to_read"]

    # ── Step 1: Google search ─────────────────────────────────────────────────
    if emit:
        await emit("agent_progress", "research", "Searching the web...")
    search_results = await asyncio.to_thread(google_search, query)

    if not search_results:
        return {
            "research_output": {"results": []},
            "agent_result": {
                "agent": "research",
                "content": "I couldn't find any web results for that question.",
                "sources": [],
                "raw": {"results": []},
            },
            "latency_ms": {**state.get("latency_ms", {}),
                           "research": int((time.time() - start) * 1000)},
        }

    # ── Step 2: Read top URLs one by one ──────────────────────────────────────
    urls_to_read = search_results[:max_urls]
    read_pages = []
    for i, result in enumerate(urls_to_read, start=1):
        if emit:
            await emit("agent_progress", "research",
                       f"Reading source {i} of {len(urls_to_read)}: {result['title'][:50]}...")
        page = await asyncio.to_thread(read_url, result["url"])
        if page["success"]:
            read_pages.append(page)

    if not read_pages:
        # Fall back to snippets if all URL reads failed
        if emit:
            await emit("agent_progress", "research",
                       "Could not read full pages, using search snippets...")
        sources_block = "\n\n".join(
            f"[{i}] {r['title']} ({r['url']})\n{r['snippet']}"
            for i, r in enumerate(search_results[:max_urls], start=1)
        )
        source_urls = [r["url"] for r in search_results[:max_urls]]
    else:
        sources_block = "\n\n".join(
            f"[{i}] {p['title']} ({p['url']})\n{p['text']}"
            for i, p in enumerate(read_pages, start=1)
        )
        source_urls = [p["url"] for p in read_pages]

    # ── Step 3: Synthesise an answer ──────────────────────────────────────────
    if emit:
        await emit("agent_progress", "research", "Synthesising answer from sources...")

    prompt = ChatPromptTemplate.from_template(_SYNTHESIS_PROMPT)
    chain = prompt | get_llm()
    answer = await asyncio.to_thread(chain.invoke, {"sources": sources_block, "question": query})

    latency = int((time.time() - start) * 1000)

    return {
        "research_output": {
            "search_results": search_results,
            "pages_read": len(read_pages),
        },
        "agent_result": {
            "agent": "research",
            "content": answer.content,
            "sources": source_urls,
            "raw": {"pages_read": len(read_pages), "urls": source_urls},
        },
        "latency_ms": {**state.get("latency_ms", {}), "research": latency},
    }
