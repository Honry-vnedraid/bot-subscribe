import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SESSION_NAME = "news_monitor_session"
