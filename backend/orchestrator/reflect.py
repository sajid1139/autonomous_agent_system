import os
import json
import asyncio
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def check(result: str, task_name: str) -> dict:
    prompt = (
        f'Rate this agent output for task "{task_name}" on a scale 1-10. '
        'Reply ONLY with a JSON object: {"score": 7, "reason": "short reason"} '
        "No markdown. No explanation. Raw JSON only.\n\n"
        f"{result}"
    )
    try:
        res = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
        )
        return json.loads(res.choices[0].message.content.strip())
    except Exception:
        return {"score": 5, "reason": "parse error"}
