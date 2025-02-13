import os
from dotenv import load_dotenv

load_dotenv()

MAX_VALUES = {
    "volume": int(os.getenv("DEX_MAX_VOLUME", 0)),
    "price_change": int(os.getenv("DEX_MAX_PRICE_CHANGE", 0)),
    "buys": int(os.getenv("DEX_MAX_BUYS", 0)),
    "liquidity": int(os.getenv("DEX_MAX_LIQUIDITY", 0)),
    "fdv": int(os.getenv("DEX_MAX_FDV", 0)),
}

WEIGHTS = {
    "volume": float(os.getenv("DEX_WEIGHT_VOLUME", 0.0)),
    "price_change": float(os.getenv("DEX_WEIGHT_PRICE_CHANGE", 0.0)),
    "buys": float(os.getenv("DEX_WEIGHT_BUYS", 0.0)),
    "liquidity": float(os.getenv("DEX_WEIGHT_LIQUIDITY", 0.0)),
    "fdv": float(os.getenv("DEX_WEIGHT_FDV", 0.0)),
}
