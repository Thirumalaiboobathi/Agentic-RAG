"""
tools/search_tools.py
---------------------
Two tools for the Research Agent:

  1. google_search(query)      — calls Google Custom Search API, returns URLs
  2. read_url(url)             — fetches a URL and extracts readable text

The Research Agent calls google_search first to get the top URLs, then
read_url on each (up to max_urls_to_read) to gather the latest content.
"""

import logging

import httpx
from bs4 import BeautifulSoup

from config.settings import settings

logger = logging.getLogger(__name__)

_cfg = settings.research
_GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


# ─── Tool 1: Google Custom Search ──────────────────────────────────────────────

def google_search(query: str, num_results: int = None) -> list[dict]:
    """
    Search Google Custom Search API.

    Returns list of dicts: {title, url, snippet}
    """
    n = num_results or _cfg["num_results"]
    params = {
        "key": _cfg["google_api_key"],
        "cx": _cfg["google_cse_id"],
        "q": query,
        "num": min(n, 10),   # CSE max is 10 per call
    }

    try:
        with httpx.Client(timeout=_cfg["fetch_timeout_seconds"]) as client:
            resp = client.get(_GOOGLE_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Google CSE HTTP error: {e.response.status_code} — {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.error(f"Google CSE request failed: {e}")
        return []

    items = data.get("items", [])
    results = [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items
    ]
    logger.info(f"Google CSE returned {len(results)} results for '{query[:60]}'")
    return results


# ─── Tool 2: Read a URL ────────────────────────────────────────────────────────

def read_url(url: str) -> dict:
    """
    Fetch a URL and extract clean readable text.

    Returns:
        {"url": str, "title": str, "text": str, "success": bool, "error": str|None}
    """
    max_chars = _cfg["max_chars_per_page"]
    timeout = _cfg["fetch_timeout_seconds"]
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/1.0)"
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return {"url": url, "title": "", "text": "", "success": False, "error": str(e)}

    try:
        soup = BeautifulSoup(html, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator="\n", strip=True)

        # Collapse blank lines and truncate
        import re
        text = re.sub(r"\n{3,}", "\n\n", text)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"

    except Exception as e:
        logger.warning(f"Failed to parse {url}: {e}")
        return {"url": url, "title": "", "text": "", "success": False, "error": str(e)}

    logger.info(f"Read URL {url} — {len(text)} chars extracted")
    return {"url": url, "title": title, "text": text, "success": True, "error": None}
