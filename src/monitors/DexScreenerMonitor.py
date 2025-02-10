import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from utils.Notifier import Notifier

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DEXSCREENER_API_BASE = "https://api.dexscreener.com"
LATEST_TOKENS_ENDPOINT = "/token-profiles/latest/v1"
BOOSTED_TOKENS_ENDPOINT = "/token-boosts/latest/v1"


class DexScreenerMonitor:
    def __init__(self, notifier: Notifier, interval=60):
        self.notifier = notifier
        self.interval = interval
        self.last_token_ids = set()  # To track newly detected tokens
        self.last_boosted_ids = set()  # To track boosted tokens

    async def fetch_json(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error fetching {url}: {response.status}")
                    return None

    async def get_latest_tokens(self):
        """Fetch latest token profiles."""
        url = DEXSCREENER_API_BASE + LATEST_TOKENS_ENDPOINT
        data = await self.fetch_json(url)
        if data is None:
            print("Error fetching latest token profiles")
            return []

        return data  # Directly return the list of token profiles

    async def get_boosted_tokens(self):
        """Fetch latest boosted tokens."""
        url = DEXSCREENER_API_BASE + BOOSTED_TOKENS_ENDPOINT
        data = await self.fetch_json(url)
        if data is None:
            print("Error fetching latest boosted tokens")
            return []

        return data  # Directly return the list of boosted tokens

    async def process_latest_tokens(self):
        """Monitor newly listed tokens."""
        tokens = await self.get_latest_tokens()
        if not tokens:
            return

        new_tokens = [token for token in tokens if token["tokenAddress"] not in self.last_token_ids]
        if not new_tokens:
            return

        for token in new_tokens:
            message = (
                f"🚀 **New Token Listed**\n\n"
                f"**Chain:** {token['chainId'].capitalize()}\n"
                f"**Token Address:** `{token['tokenAddress']}`\n"
                f"🔗 [View on DexScreener]({token['url']})\n"
                f"📝 Description: {token.get('description', 'No description available')}\n"
            )
            await self.notifier.send_message(message)

        self.last_token_ids.update(token["tokenAddress"] for token in new_tokens)

    async def process_boosted_tokens(self):
        """Monitor boosted tokens with high momentum."""
        tokens = await self.get_boosted_tokens()
        if not tokens:
            return

        boosted_tokens = [token for token in tokens if token["tokenAddress"] not in self.last_boosted_ids]
        if not boosted_tokens:
            return

        for token in boosted_tokens:
            message = (
                f"📈 **Trending Token Alert**\n\n"
                f"**Chain:** {token['chainId'].capitalize()}\n"
                f"**Token Address:** `{token['tokenAddress']}`\n"
                f"🔥 Boost Score: {token.get('amount', 'N/A')}\n"
                f"🔗 [View on DexScreener]({token['url']})\n"
                f"📝 Description: {token.get('description', 'No description available')}\n"
            )
            await self.notifier.send_message(message)

        self.last_boosted_ids.update(token["tokenAddress"] for token in boosted_tokens)

    async def run(self):
        """Main monitoring loop."""
        while True:
            try:
                await self.process_latest_tokens()
                await self.process_boosted_tokens()
            except Exception as e:
                print(f"DexScreenerMonitor error: {e}")

            await asyncio.sleep(self.interval)
