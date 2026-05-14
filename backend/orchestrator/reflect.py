import os
import json
from google import genai

async def check(result: str, task_name: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = (
        f'Rate this agent output for task "{task_name}" on a scale 1-10. '
        'Reply ONLY with a JSON object: {"score": 7, "reason": "short reason"} '
        "No markdown. No explanation. Raw JSON only.\n\n"
        f"{result}"
    )
    try:
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return json.loads(res.text.strip())
    except Exception:
        return {"score": 5, "reason": "parse error"}
