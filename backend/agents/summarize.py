import os
import asyncio
from openai import OpenAI
from agents.base import Agent

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SummarizeAgent(Agent):
    def __init__(self):
        super().__init__("summarize")

    async def run(self, task, ctx: dict):
        try:
            content = "\n\n".join(str(v) for v in ctx.values()) if ctx else task.name
            prompt = f"Summarize this concisely: {content}"
            res = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            print("AGENT ERROR [summarize]:", str(e))
            return ""

async def run(task, ctx: dict):
    return await SummarizeAgent().run(task, ctx)
