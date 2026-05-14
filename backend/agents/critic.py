import os
from google import genai
from agents.base import Agent

class CriticAgent(Agent):
    def __init__(self):
        super().__init__("critic")

    async def run(self, task, ctx: dict):
        content = list(ctx.values())[-1] if ctx else task.name
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Rate this output 1-10 and explain briefly: {content}",
        )
        return res.text.strip()

async def run(task, ctx: dict):
    return await CriticAgent().run(task, ctx)
