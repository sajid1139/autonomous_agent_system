import os
import asyncio
from openai import OpenAI
from agents.base import Agent

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ValidateAgent(Agent):
    def __init__(self):
        super().__init__("validate")

    async def run(self, task, ctx: dict):
        try:
            content = list(ctx.values())[-1] if ctx else task.name
            prompt = f"Check this for factual issues or hallucinations: {content}"
            res = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            print("AGENT ERROR [validate]:", str(e))
            return ""

async def run(task, ctx: dict):
    return await ValidateAgent().run(task, ctx)
