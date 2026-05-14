from orchestrator.reflect import check

async def with_retry(fn, task, ctx: dict, max_tries: int = 3):
    last = None
    for _ in range(max_tries):
        last = await fn(task, ctx)
        rating = await check(str(last), task.name)
        if rating.get("score", 0) >= 7:
            return last
    return last
