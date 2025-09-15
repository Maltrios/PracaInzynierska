import asyncio
import json
import os
from time import sleep

import redis
from fastapi import APIRouter, WebSocket, Depends


router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL")

r = redis.from_url(REDIS_URL)

@router.websocket("/ws/progress/{task_id}")
async def progress_bar_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        async with asyncio.timeout(60):
            while True:
                raw = r.get(f"task:{task_id}:progress")
                if raw:
                    data = json.loads(raw)
                    await websocket.send_json(data)

                    if data["progress"] >= 100 or data["progress"] == -1:
                        break

                await asyncio.sleep(0.2)
    except TimeoutError:
        await websocket.send_json({"progress": -1, "detail": "Timeout: task did not complete in time"})
    finally:
        await websocket.close()

