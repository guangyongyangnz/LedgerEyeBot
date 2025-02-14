import asyncio
import aiohttp
import os
import logging
from dotenv import load_dotenv
from utils.notifier import Notifier
from utils.config import MAX_VALUES, WEIGHTS
from utils.token_filter import TokenFilter

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
load_dotenv()

LATEST_TOKENS_ENDPOINT = os.getenv("DEX_LATEST_TOKENS_ENDPOINT")
BOOSTED_TOKENS_ENDPOINT = os.getenv("DEX_BOOSTED_TOKENS_ENDPOINT")
POOL_TOKENS_ENDPOINT = os.getenv("DEX_TOKEN_POOL_ENDPOINT")
BOOSTED_TOKENS_THRESHOLD_SCORE = float(os.getenv("DEX_BOOSTED_TOKEN_THRESHOLD_SCORE", 0))

token_filter = TokenFilter()


def normalize(value, max_value):
    return min(value / max_value, 1) * 100


def calculate_potential_score(token_data):
    try:
        volume = token_data.get("volume", {}).get("h24", 0)
        price_change_m5 = token_data.get("priceChange", {}).get("m5", 0)
        price_change_h1 = token_data.get("priceChange", {}).get("h1", 0)
        txns_buys_m5 = token_data.get("txns", {}).get("m5", {}).get("buys", 0)
        txns_buys_h1 = token_data.get("txns", {}).get("h1", {}).get("buys", 0)
        txns_sells_m5 = token_data.get("txns", {}).get("m5", {}).get("sells", 0)
        txns_m5 = txns_buys_m5 + txns_sells_m5

        # fdv = token_data.get("fdv", 0) or 0
        # liquidity = token_data.get("liquidity", {}).get("usd", 0)
        # sells = token_data.get("txns", {}).get("h24", {}).get("sells", 0)

        base_token = token_data.get("baseToken", {})
        token_address = base_token.get("address", "N/A")
        logging.info(
            f"token_address: {token_address}, volume: {volume}, price_change_m5: {price_change_m5}, price_change_h1: {price_change_h1}, buys_h24: {txns_buys_m5}, sells_h24: {txns_buys_h1}, txns_sells_m5: {txns_sells_m5}, txns_m5: {txns_m5}")

        # FOMO emotions within 5 minutes
        buys_ratio = txns_buys_m5 / max(txns_sells_m5, 1)
        volume_score = normalize(volume, MAX_VALUES["volume_h24"]) * WEIGHTS["volume_h24"]
        price_m5_score = normalize(price_change_m5, MAX_VALUES["price_change_m5"]) * WEIGHTS["price_change_m5"]
        price_h1_score = normalize(price_change_h1, MAX_VALUES["price_change_h1"]) * WEIGHTS["price_change_h1"]
        txns_buys_m5_score = normalize(txns_buys_m5, MAX_VALUES["txns_buys_m5"]) * WEIGHTS["txns_buys_m5"]
        txns_buys_h1_score = normalize(txns_buys_h1, MAX_VALUES["txns_buys_h1"]) * WEIGHTS["txns_buys_h1"]
        txns_sells_m5_score = normalize(txns_sells_m5, MAX_VALUES["txns_sells_m5"]) * WEIGHTS["txns_sells_m5"]
        txns_score = normalize(txns_m5, MAX_VALUES["txns_m5"]) * WEIGHTS["txns_m5"]

        # extra bonus
        buys_boost = 5 if buys_ratio > 2 else 0
        total_score = volume_score + price_m5_score + price_h1_score + txns_buys_m5_score + txns_buys_h1_score + txns_sells_m5_score + txns_score + buys_boost
        return round(total_score, 2)
    except Exception as e:
        logging.error(f"calculate_potential_score error: {e}")
        return 0.00


async def fetch_json(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.info(f"Error fetching {url}: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"fetch_json error: {e}")
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
    try:
        url = f"{POOL_TOKENS_ENDPOINT}/{chain_id}/{token_address}"
        data = await fetch_json(url)

        if isinstance(data, list):
            pool_data = data
        elif isinstance(data, dict) and "pairs" in data:
            pool_data = data["pairs"]
        else:
            return None

        if not pool_data:
            return None

        # A token may have multiple trading pairs, select the highest liquidity pair to score the token
        best_pool_data = max(pool_data, key=lambda x: x.get("liquidity", {}).get("usd", 0), default=None)
        return best_pool_data
    except Exception as e:
        logging.error(f"Error fetching pool tokens: {e}")
        return None


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
        try:
            tokens = await get_boosted_tokens()
            if not tokens:
                return

            for token in tokens:
                chain_id = token.get("chainId")
                token_address = token.get("tokenAddress")
                if not chain_id or not token_address:
                    continue

                pool_token_detail = await fetch_pool_tokens(chain_id, token_address)
                if not pool_token_detail:
                    continue

                if not token_filter.filter_token(pool_token_detail):
                    logging.info(f"Token {token_address} does not meet the filter criteria")
                    continue

                potential_score = calculate_potential_score(pool_token_detail)
                logging.info(f"token_address: {token_address}, Potential score: {potential_score}")
                if potential_score >= BOOSTED_TOKENS_THRESHOLD_SCORE:
                    await self.send_potential_token_alert(pool_token_detail, potential_score)
        except Exception as e:
            logging.error(f"Error processing boosted tokens: {e}")

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
