import os
from tavily import TavilyClient
from agents.base import Agent
from memory import vec

class ResearchAgent(Agent):
    def __init__(self):
        super().__init__("research")

    async def run(self, task, ctx: dict):
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        res = client.search(query=task.name, max_results=3)
        parts = [r.get("content", "") for r in res.get("results", [])]
        result = "\n\n".join(parts)
        await vec.store(result, str(task.goal_id))
        return result

async def run(task, ctx: dict):
    return await ResearchAgent().run(task, ctx)
