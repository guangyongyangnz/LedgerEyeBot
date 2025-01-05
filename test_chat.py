import os

from telegram import Bot
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def send_telegram_message(token, chat_id, message):

    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message)
        print("Message Send Successfully！")
    except Exception as e:
        print(f"Message Send Fail: {e}")


if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    MESSAGE = "Hello, this is a message from your Python program!"

    asyncio.run(send_telegram_message(TOKEN, CHAT_ID, MESSAGE))
