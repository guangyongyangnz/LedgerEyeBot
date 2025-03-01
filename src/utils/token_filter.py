import logging
import time

from utils.chain_analytics import ChainAnalytics


class TokenFilter:
    def __init__(self):
        self.min_liquidity = 80000
        self.min_volume_h24 = 10000
        self.max_fdv_ratio = 1000
        self.min_price_change = 0.50
        self.min_buys_h24 = 20

    def filter_token(self, token_data):
        try:
            liquidity = token_data.get("liquidity", {}).get("usd", 0)
            volume_h24 = token_data.get("volume", {}).get("h24", 0)
            price_change_m5 = token_data.get("priceChange", {}).get("m5", 0)
            price_change_h1 = token_data.get("priceChange", {}).get("h1", 0)
            price_change_h6 = token_data.get("priceChange", {}).get("h6", 0)
            price_change_h24 = token_data.get("priceChange", {}).get("h24", 0)
            fdv = token_data.get("fdv", 0) or 1
            token_age = time.time() - (token_data.get("pairCreatedAt", 0) / 1000)
            buys_h24 = token_data.get("txns", {}).get("h24", {}).get("buys", 0)
            volume_m5 = token_data["volume"]["m5"]
            txns_m5 = token_data["txns"]["m5"]["buys"] + token_data["txns"]["m5"]["sells"]

            logging.info(f"liquidity: {liquidity}, volume_24h: {volume_h24}, price_change_m5: {price_change_m5},"
                         f" fdv: {fdv}, txns_5m: {txns_m5}, token_age: {token_age}, buys_24h: {buys_h24}, volume_5m: {volume_m5}")

            dynamic_fdv_ration = min(5000, max(1000, token_age * 2))
            fdv_ratio = fdv / liquidity if liquidity > 0 else float("inf")
            if liquidity < self.min_liquidity or volume_h24 < self.min_volume_h24:
                logging.error("liquidity failed")
                return False

            # if fdv_ratio > dynamic_fdv_ration:
            #     logging.error(f"fdv_ratio failed: {fdv_ratio}, dynamic_fdv_ration: {dynamic_fdv_ration}")
            #     return False

            if buys_h24 < self.min_buys_h24:
                logging.error("buys_24h failed")
                return False

            if (price_change_m5 < self.min_price_change
                    and price_change_h1 < self.min_price_change
                    and price_change_h6 < self.min_price_change
                    and price_change_h24 < self.min_price_change):
                logging.error("price_change_m5 failed")
                return False

            # filter out bot manipulate the market
            if volume_m5 > 0.5 * volume_h24 and txns_m5 < 10:
                logging.error("volume_m5 or txns_m5 failed")
                return False

            if not token_data["info"]["socials"]:
                logging.error("socials not found")
                return False

            return True
        except Exception as e:
            print(f"TokenFilter error: {e}")
            return False
