from telethon import TelegramClient, events, functions
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.types import MessageEntityUrl
import httpx
from datetime import datetime
import asyncio
from config import API_ID, API_HASH, PHONE_NUMBER, WEBHOOK_URL, SESSION_NAME

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
monitored_channels = set()

def extract_urls(message):
    urls = []
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, MessageEntityUrl):
                urls.append(message.text[entity.offset:entity.offset + entity.length])
    return urls[0] if urls else None

async def send_to_webhook(data):
    async with httpx.AsyncClient() as http_client:
        try:
            response = await http_client.post(
                WEBHOOK_URL,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[Webhook Error] {e}")

async def send_to_microservice(data):
    url = "http://localhost:80/add/news"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
        print(f"Данные успешно отправлены на {url} — статус {response.status_code}")
    except Exception as e:
        print(f"Ошибка при отправке данных на {url}: {e}")

@client.on(events.NewMessage())
async def handle_new_post(event):
    chat = event.chat
    chat_username = getattr(chat, "username", None)
    chat_id = chat.id

    # проверка: либо по username, либо по id
    if chat_username and chat_username in monitored_channels:
        pass  # ok
    elif chat_id and str(chat_id) in monitored_channels:
        pass  # ok
    else:
        return

    post_data = {
        "source": chat_username or chat.title or str(chat_id),
        "text": event.raw_text,
        "date": event.date.isoformat(),
        "url": f"https://t.me/{chat_username}/{event.id}" if chat_username else None,
    }

    await send_to_microservice(post_data)


async def subscribe_and_monitor(channel_username: str) -> str:
    try:
        entity = await client.get_entity(channel_username)
        await client(functions.channels.JoinChannelRequest(channel=entity))
    except UserAlreadyParticipantError:
        pass

    if entity.username:
        monitored_channels.add(entity.username)
    monitored_channels.add(str(entity.id))  # как fallback
    return entity.title
