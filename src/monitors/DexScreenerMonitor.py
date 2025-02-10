import requests
from telegram import Bot
import asyncio


class DexScreenerMonitor:
    def __init__(self, telegram_token, chat_id):
        self.api_url = "https://api.dexscreener.io/latest/dex/pairs"
        self.bot = Bot(token=telegram_token)
        self.chat_id = chat_id
        self.chains = ["ethereum", "solana"]
        self.volume_threshold = 100000
        self.price_change_threshold = 10

    async def fetch_trending_pairs(self, chain):
        try:
            url = f"{self.api_url}/{chain}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            trending_pairs = []
            for pair in data.get("pairs", []):
                volume_usd = float(pair["volume"]["h24"])
                price_change = float(pair["priceChange"]["h24"])

                if volume_usd >= self.volume_threshold or abs(price_change) >= self.price_change_threshold:
                    trending_pairs.append({
                        "name": pair["pairName"],
                        "price": pair["priceusd"],
                        "volume_usd": volume_usd,
                        "price_change": price_change,
                        "link": pair["url"]
                    })
            return trending_pairs
        except Exception as e:
            print(f"Error fetching trending pairs for {chain}: {e}")
            return []

    async def send_trending_alerts(self):
        for chain in self.chains:
            trending_pairs = await self.fetch_trending_pairs(chain)

            if trending_pairs:
                message = f"🔥 **Trending on {chain.capitalize()}** 🔥\n\n"
                for pair in trending_pairs:
                    message += (
                        f"🔗 **{pair['name']}**\n"
                        f"💰 **Price:** ${float(pair['price']):.4f}\n"
                        f"📈 **Volume (24h):** ${pair['volume_usd']:,}\n"
                        f"📊 **Price Change (24h):** {pair['price_change']}%\n"
                        f"[View Pair]({pair['link']})\n\n"
                    )

                try:
                    await self.bot.send_message(chat_id=self.chat_id, text=message)
                except Exception as e:
                    print(f"Error sending alert for {chain}: {e}")

    async def monitor_trending(self, interval=600):
        while True:
            await self.send_trending_alerts()
            await asyncio.sleep(interval)
