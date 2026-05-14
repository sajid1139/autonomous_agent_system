import re

blocked = ["hack", "exploit", "malware", "virus"]
url_re = re.compile(r"https?://\S+")

async def check(goal_text: str) -> bool:
    if url_re.match(goal_text.strip()):
        return True
    if len(goal_text) > 500:
        raise ValueError("too long")
    low = goal_text.lower()
    for word in blocked:
        if word in low:
            raise ValueError("not allowed")
    return True
