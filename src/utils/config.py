import os
from dotenv import load_dotenv

load_dotenv()

MAX_VALUES = {
    "volume": int(os.getenv("DEX_MAX_VOLUME", 1000000)),
    "price_change": int(os.getenv("DEX_MAX_PRICE_CHANGE", 500)),
    "buys": int(os.getenv("DEX_MAX_BUYS", 20000)),
    "liquidity": int(os.getenv("DEX_MAX_LIQUIDITY", 200000)),
    "market_cap": int(os.getenv("DEX_MAX_MARKET_CAP", 1000000)),
}

WEIGHTS = {
    "volume": float(os.getenv("DEX_WEIGHT_VOLUME", 0.3)),
    "price_change": float(os.getenv("DEX_WEIGHT_PRICE_CHANGE", 0.2)),
    "buys": float(os.getenv("DEX_WEIGHT_BUYS", 0.25)),
    "liquidity": float(os.getenv("DEX_WEIGHT_LIQUIDITY", 0.15)),
    "market_cap": float(os.getenv("DEX_WEIGHT_MARKET_CAP", 0.1)),
}
