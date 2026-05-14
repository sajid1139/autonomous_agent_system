from models.session import Session

async def save(goal_id: str, key: str, value):
    rec, _ = await Session.get_or_create(goal_id=goal_id, defaults={"state": {}})
    rec.state[key] = value
    await rec.save()

async def get(goal_id: str, key: str):
    rec = await Session.get_or_none(goal_id=goal_id)
    if not rec:
        return None
    return rec.state.get(key)
