from tavily import TavilyClient
import os
from config.settings import settings

client = TavilyClient(
     api_key=os.getenv("TAVILY_API_KEY")
)


def tavily_search(query: str):

    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=True,
        include_raw_content=True,
    )

    return response