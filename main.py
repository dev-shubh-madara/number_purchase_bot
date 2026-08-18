import os
import asyncio
import logging
from telethon import TelegramClient
from config import BOT_TOKEN, API_ID, API_HASH, bot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs("sessions", exist_ok=True)

# Import plugins AFTER bot is created so they can use it or register handlers
from plugins import register_all_handlers

async def main():
    print("✅ Numbott Modular (Telethon) STARTED SUCCESSFULLY")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    bot.start(bot_token=BOT_TOKEN)
    register_all_handlers(bot)

    from telethon import events
    @bot.on(events.CallbackQuery)
    async def debug_cb(e):
        logger.warning(f"CALLBACK DATA: {e.data}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

