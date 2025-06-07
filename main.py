import asyncio
import logging
import os
import re
import threading

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    FloodWaitError,
    UserAlreadyParticipantError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl import functions

# Настройки
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен вашего бота
API_ID = os.getenv("API_ID")  # Ваш API ID от https://my.telegram.org
API_HASH = os.getenv("API_HASH")  # Ваш API Hash от https://my.telegram.org
PHONE_NUMBER = os.getenv("PHONE_NUMBER")  # Номер телефона сервисного аккаунта

# Проверка, что все переменные окружения загружены
if not all([BOT_TOKEN, API_ID, API_HASH, PHONE_NUMBER]):
    raise ValueError(
        "Не все переменные окружения (BOT_TOKEN, API_ID, API_HASH, PHONE_NUMBER) установлены. Проверьте ваш .env файл."
    )

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные для клиента
client = None
client_loop = None


def extract_channel_username(url):
    """Извлекает username канала из различных форматов ссылок"""
    patterns = [
        r"t\.me/([a-zA-Z0-9_]+)",
        r"telegram\.me/([a-zA-Z0-9_]+)",
        r"@([a-zA-Z0-9_]+)",
        r"([a-zA-Z0-9_]+)$",  # Просто username
    ]

    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            username = match.group(1)
            # Убираем @ если есть
            return username.lstrip("@")

    return None


def run_telethon_client():
    """Запускает Telethon клиент в отдельном потоке"""
    global client, client_loop

    client_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(client_loop)

    client = TelegramClient("session_name", API_ID, API_HASH)

    async def start_client():
        await client.start(phone=PHONE_NUMBER)
        logger.info("Telethon client started successfully")
        # Держим клиент активным
        await client.run_until_disconnected()

    try:
        client_loop.run_until_complete(start_client())
    except Exception as e:
        logger.error(f"Error in Telethon client: {e}")
    finally:
        client_loop.close()


async def subscribe_to_channel(username):
    """Подписывается на канал по username"""
    global client, client_loop

    if not client or not client_loop:
        return False, "Клиент не инициализирован"

    try:
        # Выполняем операцию в цикле событий клиента
        future = asyncio.run_coroutine_threadsafe(
            _subscribe_to_channel_async(username), client_loop
        )
        return future.result(timeout=30)  # Ждем максимум 30 секунд

    except Exception as e:
        return False, f"Ошибка выполнения: {str(e)}"


async def _subscribe_to_channel_async(username):
    """Внутренняя асинхронная функция для подписки"""
    try:
        # Получаем информацию о канале
        entity = await client.get_entity(username)

        # Подписываемся на канал
        await client(functions.channels.JoinChannelRequest(entity))

        return True, f"Успешно подписался на канал: {entity.title}"

    except UserAlreadyParticipantError:
        return True, "Уже подписан на этот канал"

    except ChannelPrivateError:
        return False, "Канал приватный или не существует"

    except UsernameNotOccupiedError:
        return False, "Канал с таким username не найден"

    except UsernameInvalidError:
        return False, "Неверный формат username канала"

    except FloodWaitError as e:
        return False, f"Превышен лимит запросов. Подождите {e.seconds} секунд"

    except Exception as e:
        return False, f"Произошла ошибка: {str(e)}"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = """
🤖 Привет! Я бот для автоматической подписки на Telegram каналы.

📝 Как использовать:
1. Отправьте мне ссылку на публичный Telegram канал
2. Я автоматически подпишу ваш сервисный аккаунт на этот канал

📋 Поддерживаемые форматы ссылок:
• https://t.me/channel_name
• https://telegram.me/channel_name
• @channel_name
• channel_name

⚠️ Важно: Работает только с публичными каналами!
    """
    await update.message.reply_text(welcome_message)


async def handle_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ссылок на каналы"""
    message_text = update.message.text
    user_id = update.message.from_user.id

    # Извлекаем username канала
    channel_username = extract_channel_username(message_text)

    if not channel_username:
        await update.message.reply_text(
            "❌ Не удалось распознать ссылку на канал. "
            "Пожалуйста, отправьте корректную ссылку."
        )
        return

    # Отправляем сообщение о начале обработки
    processing_message = await update.message.reply_text(
        f"⏳ Пытаюсь подписаться на канал: @{channel_username}..."
    )

    try:
        # Подписываемся на канал
        success, result_message = await subscribe_to_channel(channel_username)

        if success:
            await processing_message.edit_text(f"✅ {result_message}")
            logger.info(
                f"User {user_id} successfully subscribed to @{channel_username}"
            )
        else:
            await processing_message.edit_text(f"❌ {result_message}")
            logger.warning(
                f"Failed to subscribe user {user_id} to @{channel_username}: {result_message}"
            )

    except Exception as e:
        error_message = f"❌ Произошла неожиданная ошибка: {str(e)}"
        await processing_message.edit_text(error_message)
        logger.error(f"Unexpected error for user {user_id}: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_message = """
🆘 Помощь по использованию бота:

📋 Команды:
/start - Запустить бота и получить приветствие
/help - Показать это сообщение помощи

🔗 Как подписаться на канал:
1. Скопируйте ссылку на публичный Telegram канал
2. Отправьте её мне в сообщении
3. Дождитесь подтверждения подписки

📝 Примеры ссылок:
• https://t.me/durov
• @durov
• durov

⚠️ Ограничения:
- Работает только с публичными каналами
- Не работает с приватными каналами и группами
- Соблюдайте лимиты Telegram API
    """
    await update.message.reply_text(help_message)


def main():
    """Основная функция"""
    try:
        # Запускаем Telethon клиент в отдельном потоке
        telethon_thread = threading.Thread(target=run_telethon_client, daemon=True)
        telethon_thread.start()

        # Ждем немного, чтобы клиент успел инициализироваться
        import time

        time.sleep(3)

        # Создаем приложение бота
        application = Application.builder().token(BOT_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))

        # Обработчик для всех текстовых сообщений (ссылки на каналы)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_link)
        )

        logger.info("Bot is starting...")

        # Запускаем бота
        application.run_polling(drop_pending_updates=True)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        # Закрываем клиент
        if client and client_loop:
            try:
                asyncio.run_coroutine_threadsafe(client.disconnect(), client_loop)
            except:
                pass


if __name__ == "__main__":
    main()
