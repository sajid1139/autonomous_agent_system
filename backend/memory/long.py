from models.task import Task

async def save_result(goal_id: str, task_name: str, result: str):
    rec = await Task.get_or_none(goal_id=goal_id, name=task_name)
    if rec:
        rec.result = result
        await rec.save()

async def get_all(goal_id: str) -> dict:
    tasks = await Task.filter(goal_id=goal_id).values("name", "result")
    return {t["name"]: t["result"] for t in tasks if t["result"]}
