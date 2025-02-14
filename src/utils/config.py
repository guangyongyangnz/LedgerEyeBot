import os
from dotenv import load_dotenv

load_dotenv()

MAX_VALUES = {
    "volume_h24": int(os.getenv("DEX_MAX_VOLUME_H24", 0)),
    "price_change_m5": int(os.getenv("DEX_MAX_PRICE_CHANGE_M5", 0)),
    "price_change_h1": int(os.getenv("DEX_MAX_PRICE_CHANGE_H1", 0)),
    "txns_buys_m5": int(os.getenv("DEX_MAX_TXNS_BUYS_M5", 0)),
    "txns_buys_h1": int(os.getenv("DEX_MAX_TXNS_BUYS_H1", 0)),
    "txns_sells_m5": int(os.getenv("DEX_MAX_TXNS_SELLS_M5", 0)),
    "txns_m5": int(os.getenv("DEX_MAX_TXNS_M5", 0)),
}

WEIGHTS = {
    "volume_h24": float(os.getenv("DEX_WEIGHT_VOLUME_H24", 0)),
    "price_change_m5": float(os.getenv("DEX_WEIGHT_PRICE_CHANGE_M5", 0)),
    "price_change_h1": float(os.getenv("DEX_WEIGHT_PRICE_CHANGE_H1", 0)),
    "txns_buys_m5": float(os.getenv("DEX_WEIGHT_TXNS_BUYS_M5", 0)),
    "txns_buys_h1": float(os.getenv("DEX_WEIGHT_TXNS_BUYS_H1", 0)),
    "txns_sells_m5": float(os.getenv("DEX_WEIGHT_TXNS_SELLS_M5", 0)),
    "txns_m5": float(os.getenv("DEX_WEIGHT_TXNS_M5", 0)),
}
