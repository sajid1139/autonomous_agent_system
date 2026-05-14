from fastapi import APIRouter
from models.task import Task
from models.report import Report

router = APIRouter()

@router.get("/sessions/{goal_id}")
async def get_session(goal_id: str):
    tasks = await Task.filter(goal_id=goal_id).order_by("order").values()
    report = await Report.get_or_none(goal_id=goal_id)
    return {
        "tasks": tasks,
        "report": {"content": report.content, "created": report.created} if report else None
    }
