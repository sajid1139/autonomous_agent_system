import os
from google import genai
from agents.base import Agent

class SummarizeAgent(Agent):
    def __init__(self):
        super().__init__("summarize")

    async def run(self, task, ctx: dict):
        content = "\n\n".join(str(v) for v in ctx.values()) if ctx else task.name
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Summarize this concisely: {content}",
        )
        return res.text.strip()

async def run(task, ctx: dict):
    return await SummarizeAgent().run(task, ctx)
