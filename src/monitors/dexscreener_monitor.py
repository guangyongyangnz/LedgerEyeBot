import asyncio
import aiohttp
import os
import logging
from dotenv import load_dotenv
from utils.notifier import Notifier
from utils.config import MAX_VALUES, WEIGHTS

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
load_dotenv()

LATEST_TOKENS_ENDPOINT = os.getenv("DEX_LATEST_TOKENS_ENDPOINT")
BOOSTED_TOKENS_ENDPOINT = os.getenv("DEX_BOOSTED_TOKENS_ENDPOINT")
POOL_TOKENS_ENDPOINT = os.getenv("DEX_TOKEN_POOL_ENDPOINT")
BOOSTED_TOKENS_THRESHOLD_SCORE = float(os.getenv("DEX_BOOSTED_TOKEN_THRESHOLD_SCORE", 10.0))


def normalize(value, max_value):
    return min(value / max_value, 1) * 100


def calculate_potential_score(token_data):
    liquidity = token_data.get("liquidity", {}).get("usd", 0)
    market_cap = token_data.get("marketCap", 0)
    volume = token_data.get("volume", {}).get("h24", 0)
    price_change = token_data.get("priceChange", {}).get("h24", 0)
    buys = token_data.get("txns", {}).get("h24", {}).get("buys", 0)
    # sells = token_data.get("txns", {}).get("h24", {}).get("sells", 0)

    base_token = token_data.get("baseToken", {})
    token_address = base_token.get("address", "N/A")
    logging.info(
        f"token_address: {token_address}, liquidity: {liquidity}, volume: {volume}, price_change: {price_change}, buys: {buys}, market_cap: {market_cap}")

    volume_score = normalize(volume, MAX_VALUES["volume"]) * WEIGHTS["volume"]
    price_change_score = normalize(price_change, MAX_VALUES["price_change"]) * WEIGHTS["price_change"]
    buys_score = normalize(buys, MAX_VALUES["buys"]) * WEIGHTS["buys"]
    liquidity_score = normalize(liquidity, MAX_VALUES["liquidity"]) * WEIGHTS["liquidity"]
    market_cap_score = normalize(market_cap, MAX_VALUES["market_cap"]) * WEIGHTS["market_cap"]

    total_score = volume_score + price_change_score + buys_score + liquidity_score + market_cap_score

    return round(total_score, 2)


async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                logging.info(f"Error fetching {url}: {response.status}")
                return None


async def get_latest_tokens():
    data = await fetch_json(LATEST_TOKENS_ENDPOINT)
    if data is None:
        logging.info("Error fetching latest token profiles")
        return []

    logging.info("Latest tokens fetched")
    return data


async def get_boosted_tokens():
    data = await fetch_json(BOOSTED_TOKENS_ENDPOINT)

    if isinstance(data, list):
        return data
    return []


async def fetch_pool_tokens(chain_id, token_address):
    url = f"{POOL_TOKENS_ENDPOINT}/{chain_id}/{token_address}"
    data = await fetch_json(url)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "pairs" in data:
        return data["pairs"]
    return []


class DexScreenerMonitor:
    def __init__(self, notifier: Notifier, interval=60):
        self.notifier = notifier
        self.interval = interval
        self.last_token_ids = set()
        self.last_boosted_ids = set()

    async def process_latest_tokens(self):
        """Monitor newly listed tokens."""
        tokens = await get_latest_tokens()
        if not tokens:
            print("No new tokens")
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
        tokens = await get_boosted_tokens()
        if not tokens:
            return

        boosted_tokens = [token for token in tokens if token.get("tokenAddress") not in self.last_boosted_ids]
        if not boosted_tokens:
            return

        for token in boosted_tokens:
            chain_id = token.get("chainId")
            token_address = token.get("tokenAddress")

            if not chain_id or not token_address:
                continue

            token_details = await fetch_pool_tokens(chain_id, token_address)
            if not token_details:
                continue

            for token_data in token_details:
                token_address = token_data.get("baseToken", {}).get('address', 'N/A')

                # filter out fake token
                if token_data["fdv"] > 50_000_000 and token_data["liquidity"]["usd"] < 50_000:
                    logging.info(f"token_address: {token_address} maybe a fake token")
                    continue

                # filter out bot manipulate the market
                volume_5m = token_data["volume"]["m5"]
                volume_24h = token_data["volume"]["h24"]
                txns_5m = token_data["txns"]["m5"]["buys"] + token_data["txns"]["m5"]["sells"]
                if volume_5m > 0.5 * volume_24h and txns_5m < 10:
                    logging.info(f"token_address: {token_address} maybe a bot manipulated token")
                    continue

                # filter out no social media account
                if not token_data["info"]["socials"]:
                    logging.info(f"token_address: {token_address} no social platform")
                    continue

                potential_score = calculate_potential_score(token_data)

                if potential_score >= BOOSTED_TOKENS_THRESHOLD_SCORE:
                    await self.send_potential_token_alert(token_data, potential_score)

        self.last_boosted_ids.update(token["tokenAddress"] for token in boosted_tokens)

    async def send_potential_token_alert(self, token_data, potential_score):
        base_token = token_data.get("baseToken", {})
        name = base_token.get("name", "Unknown")
        symbol = base_token.get("symbol", "N/A")
        address = base_token.get("address", "N/A")
        chain_id = token_data.get("chainId", "N/A")
        liquidity = token_data.get("liquidity", {}).get("usd", 0)
        volume = token_data.get("volume", {}).get("h24", 0)
        price_change = token_data.get("priceChange", {}).get("h24", 0)
        buys = token_data.get("txns", {}).get("h24", {}).get("buys", 0)
        sells = token_data.get("txns", {}).get("h24", {}).get("sells", 0)
        url = f"https://dexscreener.com/{chain_id}/{address}"

        message = (
            f"🚀 **Potential Token Alert** 🚀\n\n"
            f"🔹 **{name}** ($ {symbol})\n"
            f"🔗 **Chain ID:** {chain_id}\n"
            f"📜 **Contract Address:** `{address}`\n"
            f"💰 **Liquidity:** ${liquidity:,.0f}\n"
            f"📊 **24H Trading Volume:** ${volume:,.0f}\n"
            f"📈 **24H Price Change:** {price_change:.2f}%\n"
            f"🛒 **Buy Transactions:** {buys}\n"
            f"📉 **Sell Transactions:** {sells}\n"
            f"🔥 **Potential Score:** {potential_score:.2f}\n\n"
            f"🔍 [View on DexScreener]({url})"
        )

        await self.notifier.send_message(message)

    async def run(self):
        """Main monitoring loop."""
        while True:
            try:
                # await self.process_latest_tokens()
                await self.process_boosted_tokens()
            except Exception as e:
                logging.error(f"DexScreenerMonitor error: {e}")

            await asyncio.sleep(self.interval)
