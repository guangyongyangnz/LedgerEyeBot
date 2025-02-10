import asyncio
import requests
import time

DEXSCREENER_API_BASE_URL = "https://api.dexscreener.com"
TOKEN_REFRESH_INTERVAL = 60

class DexScreenerMonitor:
    def __init__(self, notifier):
        self.notifier = notifier
        self.last_checked_time = time.time()

    async def fetch_latest_tokens(self):
        url = f"{DEXSCREENER_API_BASE_URL}/token-profiles/latest/v1"
        return self._fetch_tokens(url, "Latest Token Listings")

    async def fetch_boosted_tokens(self):
        url = f"{DEXSCREENER_API_BASE_URL}/token-boosts/latest/v1"
        return self._fetch_tokens(url, "Boosted Trending Tokens")

    def _fetch_tokens(self, url, category):
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"⚠️ [DexScreener] API Request Failed: {response.status_code}")
                return None

            data = response.json()
            tokens = data.get("tokens", [])
            return self._process_tokens(tokens, category)

        except requests.RequestException as e:
            print(f"⚠️ [DexScreener] Request Failed: {e}")
            return None

    def _process_tokens(self, tokens, category):
        if not tokens:
            print(f"📭 [DexScreener] No {category} data")
            return

        message = f"🔥 **[{category}]**\n\n"

        for token in tokens[:5]:
            name = token.get("name", "Unknown")
            symbol = token.get("symbol", "???")
            price = token.get("priceUsd", "N/A")
            liquidity = token.get("liquidity", "N/A")
            url = f"https://dexscreener.com/{token.get('chainId', 'unknown')}/{token.get('address', '')}"

            message += f"💎 **{name}** ({symbol})\n"
            message += f"💰 Price: `{price} USD`\n"
            message += f"📊 Liquidity: `{liquidity} USD`\n"
            message += f"[🔗 View on Dexscreener]({url})\n\n"

        asyncio.create_task(self.notifier.send_message(message))

    async def monitor_tokens(self):
        while True:
            await self.fetch_latest_tokens()
            await self.fetch_boosted_tokens()
            await asyncio.sleep(TOKEN_REFRESH_INTERVAL)