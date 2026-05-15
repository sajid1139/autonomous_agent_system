import os
import json
import asyncio
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sys_prompt = (
    "You are an autonomous task planner. Given a user goal, decompose it into 3-6 subtasks. "
    "Return ONLY a JSON array. Each item must have: "
    "- name: short task name "
    "- agent: one of [research, summarize, critic, validate, execute, report] "
    "- depends_on: list of task names this depends on (empty list if none) "
    "Rules you must follow: "
    "1. The task list must always include exactly one task with agent 'research'. "
    "2. The task list must always include exactly one task with agent 'summarize'. "
    "3. The LAST task in the array must always have agent 'report'. It generates the final report. "
    "4. The report task must depend on all other tasks before it. "
    "No explanation. No markdown. Only raw JSON array."
)

fallback = [
    {"name": "research", "agent": "research", "depends_on": []},
    {"name": "summarize", "agent": "summarize", "depends_on": ["research"]},
    {"name": "report", "agent": "report", "depends_on": ["summarize"]},
]

async def plan(goal_text: str) -> list[dict]:
    try:
        res = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": goal_text},
                ]
            )
        )
        raw = res.choices[0].message.content.strip()
        tasks = json.loads(raw)
        if isinstance(tasks, list) and len(tasks) > 0:
            return tasks
        return fallback
    except Exception:
        return fallback
