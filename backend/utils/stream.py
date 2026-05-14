import asyncio
from fastapi import WebSocket

queues: dict[str, asyncio.Queue] = {}

def get_queue(goal_id: str) -> asyncio.Queue:
    if goal_id not in queues:
        queues[goal_id] = asyncio.Queue()
    return queues[goal_id]

async def notify(goal_id: str, msg: str):
    q = get_queue(goal_id)
    await q.put(msg)

async def ws_endpoint(websocket: WebSocket, goal_id: str):
    await websocket.accept()
    q = get_queue(goal_id)
    try:
        while True:
            msg = await q.get()
            await websocket.send_text(msg)
    except Exception:
        queues.pop(goal_id, None)
