from telegram import Bot
from telegram.constants import ParseMode


class Notifier:
    def __init__(self, token, chat_id):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    async def send_message(self, message):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            print(f"Notifier error: {e}")
