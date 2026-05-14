import os
from tavily import TavilyClient

async def run(query: str) -> str:
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    res = client.search(query=query, max_results=3)
    parts = [r.get("content", "") for r in res.get("results", [])]
    return "\n\n".join(parts)
