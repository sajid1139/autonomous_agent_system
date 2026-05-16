import os
import asyncio
from datetime import datetime
import pytz
from openai import OpenAI
from agents.base import Agent
from models.goal import Goal
from models.report import Report

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ReportAgent(Agent):
    def __init__(self):
        super().__init__("report")

    async def run(self, task, ctx: dict):
        try:
            pk_tz = pytz.timezone("Asia/Karachi")
            now = datetime.now(pk_tz).strftime("%B %d, %Y %I:%M %p PKT")
            goal = await Goal.get_or_none(id=task.goal_id)
            goal_text = goal.text if goal else ""
            research = ctx.get("research", "")
            summary = ctx.get("summarize", "")
            prompt = f"""Answer this question directly and concisely:

Question/Goal: {goal_text}

Research: {research}

Summary: {summary}

Date: {now}

Rules:
- Answer only what was asked
- No formal headers like Title, Author, Department
- No "Professional Structured Report" text
- Use simple headings only if needed
- Be direct and to the point
- Include only relevant information"""
            res = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=30
                )
            )
            text = res.choices[0].message.content.strip()
            await Report.create(goal_id=task.goal_id, content=text)
            return text
        except Exception as e:
            print("AGENT ERROR [report]:", str(e))
            return ""

async def run(task, ctx: dict):
    return await ReportAgent().run(task, ctx)
