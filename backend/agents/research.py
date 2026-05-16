import os
import asyncio
from tavily import TavilyClient
from agents.base import Agent
from memory import vec

class ResearchAgent(Agent):
    def __init__(self):
        super().__init__("research")

    async def run(self, task, ctx: dict):
        try:
            client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            res = await asyncio.to_thread(client.search, query=task.name, max_results=3)
            parts = [r.get("content", "") for r in res.get("results", [])]
            result = "\n\n".join(parts)
            await vec.store(result, str(task.goal_id))
            return result
        except Exception as e:
            print("AGENT ERROR [research]:", str(e))
            return ""

async def run(task, ctx: dict):
    return await ResearchAgent().run(task, ctx)
