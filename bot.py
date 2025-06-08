import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackContext,
    filters
)
import requests
import asyncio

# Настройки
TOKEN = "8144928136:AAH82t_KZMOwxnSqlZ1Sm5SF7O1QH24Pewk"
BACKEND_URL = "http://10.10.126.2:8080/subscribe"

# Логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def normalize_link(text: str) -> str | None:
    """Преобразует текст в ссылку формата https://t.me/name"""
    text = text.strip()
    if text.startswith('https://t.me/'):
        return text
    elif text.startswith('t.me/'):
        return 'https://' + text
    elif text.startswith('@'):
        return 'https://t.me/' + text[1:]
    return None

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обрабатывает любое текстовое сообщение и отправляет на бэкенд"""
    text = update.message.text
    link = normalize_link(text)
    if not link:
        return  # Ничего не делаем, если ссылка нераспознаваема

    url = f"{BACKEND_URL}?link={link}"
    logger.info(f"Отправка ссылки: {url}")

    def send_to_backend():
        try:
            return requests.get(url, timeout=5)
        except Exception as e:
            logger.error(f"Ошибка при отправке запроса: {e}")
            return None

    response = await asyncio.get_event_loop().run_in_executor(None, send_to_backend)
    if response and response.status_code == 200:
        logger.info(f"Успешно отправлено: {link}")
    else:
        logger.warning(f"Не удалось отправить: {link} — статус {response.status_code if response else 'нет ответа'}")

async def start(update: Update, context: CallbackContext) -> None:
    """Заглушка для /start"""
    pass

def main() -> None:
    """Запуск"""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
