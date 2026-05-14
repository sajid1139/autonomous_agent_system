import os
from google import genai
from agents.base import Agent

class ExecuteAgent(Agent):
    def __init__(self):
        super().__init__("execute")

    async def run(self, task, ctx: dict):
        content = list(ctx.values())[-1] if ctx else ""
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        prompt = f"Based on this context, perform the task: {task.name}. Context: {content}"
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return res.text.strip()

async def run(task, ctx: dict):
    return await ExecuteAgent().run(task, ctx)
