import os
from google import genai
from agents.base import Agent
from models.report import Report

class ReportAgent(Agent):
    def __init__(self):
        super().__init__("report")

    async def run(self, task, ctx: dict):
        all_ctx = "\n\n".join(f"{k}: {v}" for k, v in ctx.items())
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        prompt = (
            "Generate a professional structured report with Summary, Findings, "
            f"Recommendations sections based on: {all_ctx}"
        )
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = res.text.strip()
        await Report.create(goal_id=task.goal_id, content=text)
        return text

async def run(task, ctx: dict):
    return await ReportAgent().run(task, ctx)
