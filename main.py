from config import PHONE_NUMBER
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
import re
import asyncio

from telegram_client import client, subscribe_and_monitor

app = FastAPI()

class SubscribeRequest(BaseModel):
    channel: str  # может быть @durov, t.me/durov или просто durov

def extract_username(channel: str) -> str | None:
    patterns = [r"t\.me/([a-zA-Z0-9_]+)", r"@([a-zA-Z0-9_]+)", r"^([a-zA-Z0-9_]+)$"]
    for pattern in patterns:
        match = re.search(pattern, channel.strip())
        if match:
            return match.group(1)
    return None

@app.post("/subscribe")
async def subscribe(request: SubscribeRequest):
    username = extract_username(request.channel)
    if not username:
        return {"status": "error", "message": "Invalid channel format"}

    try:
        title = await subscribe_and_monitor(username)
        return {"status": "ok", "channel": username, "title": title}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def startup():
    await client.start(phone=PHONE_NUMBER)
    print("Telegram client started")

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(startup())

@app.on_event("shutdown")
async def on_shutdown():
    await client.disconnect()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
