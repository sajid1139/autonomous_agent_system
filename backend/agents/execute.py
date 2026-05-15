import os
import asyncio
from openai import OpenAI
from agents.base import Agent

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ExecuteAgent(Agent):
    def __init__(self):
        super().__init__("execute")

    async def run(self, task, ctx: dict):
        try:
            content = list(ctx.values())[-1] if ctx else ""
            prompt = f"Based on this context, perform the task: {task.name}. Context: {content}"
            res = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            print("AGENT ERROR [execute]:", str(e))
            return ""

async def run(task, ctx: dict):
    return await ExecuteAgent().run(task, ctx)
