import time


class TokenFilter:
    def __init__(self):
        self.min_liquidity = 100_000
        self.min_volume_24h = 50_000
        self.max_fdv_ratio = 50
        self.max_age_hours = 2
        self.min_price_change = 25
        self.min_buys_24h = 1000

    def filter_token(self, token_data):
        try:
            liquidity = token_data.get("liquidity", {}).get("usd", 0)
            volume_24h = token_data.get("volume", {}).get("h24", 0)
            price_change_m5 = token_data.get("priceChange", {}).get("m5", 0)
            fdv = token_data.get("fdv", 0) or 1
            token_age = time.time() - (token_data.get("pairCreatedAt", 0) / 1000)
            buys_24h = token_data.get("txns", {}).get("h24", {}).get("buys", 0)
            volume_5m = token_data["volume"]["m5"]
            txns_5m = token_data["txns"]["m5"]["buys"] + token_data["txns"]["m5"]["sells"]

            fdv_ratio = fdv / max(liquidity, 1)
            if liquidity < self.min_liquidity or volume_24h < self.min_volume_24h:
                return False

            if fdv_ratio > self.max_fdv_ratio:
                return False

            if buys_24h < self.min_buys_24h:
                return False

            if token_age > self.max_age_hours * 3600 or price_change_m5 < self.min_price_change:
                return False

            # filter out bot manipulate the market
            if volume_5m > 0.5 * volume_24h and txns_5m < 10:
                return False

            if not token_data["info"]["socials"]:
                return False

            return True
        except Exception as e:
            print(f"TokenFilter error: {e}")
            return False
