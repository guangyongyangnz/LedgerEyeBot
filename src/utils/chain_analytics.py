import asyncio
import os

import aiohttp
import logging
from datetime import datetime, timedelta
from solana.rpc.async_api import AsyncClient
from solders.signature import Signature
from base58 import b58encode, b58decode
from dotenv import load_dotenv

load_dotenv()
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")


class ChainAnalytics:
    def __init__(self):
        self.solana_client = AsyncClient(SOLANA_RPC_URL)

    def get_solana_token_accounts(self, token_address):
        try:
            response = self.solana_client.get_token_accounts_by_mint(token_address)
            if response.value:
                return response.value
            return []
        except Exception as e:
            logging.error(f"Error getting Solana token accounts: {e}")
            return []

    def get_solana_daily_active_addresses(self, token_address, days=1):
        try:
            recent_blocks = self.solana_client.get_signatures_for_address(
                token_address,
                limit=1000
            )

            if not recent_blocks.value:
                return 0

            current_time = datetime.now()
            start_time = current_time - timedelta(days=days)

            unique_addresses = set()

            for sig in recent_blocks.value:
                tx_time = datetime.fromtimestamp(sig.block_time)
                if tx_time < start_time:
                    continue

                tx = self.solana_client.get_transaction(
                    Signature.from_string(sig.signature)
                )

                if tx.value:
                    for account in tx.value.transaction.message.account_keys:
                        unique_addresses.add(str(account))

            return len(unique_addresses)

        except Exception as e:
            logging.error(f"Error getting Solana daily active addresses: {e}")
            return 0

    def get_solana_token_holders_distribution(self, token_address):
        try:
            accounts = self.get_solana_token_accounts(token_address)
            if not accounts:
                return {}

            holdings = {}
            total_supply = 0

            for account in accounts:
                balance = int(account.account.data.parsed['info']['tokenAmount']['amount'])
                holder = account.pubkey
                holdings[holder] = balance
                total_supply += balance

            distribution = {
                'total_holders': len(holdings),
                'total_supply': total_supply,
                'top_10_percentage': 0,
                'concentration_index': 0
            }

            if total_supply > 0:
                sorted_holdings = sorted(holdings.values(), reverse=True)
                top_10_sum = sum(sorted_holdings[:10])
                distribution['top_10_percentage'] = (top_10_sum / total_supply) * 100

                distribution['concentration_index'] = sum(
                    (balance / total_supply) ** 2 for balance in holdings.values())

            return distribution

        except Exception as e:
            logging.error(f"Error getting Solana token holders distribution: {e}")
            return {}

    def get_solana_token_liquidity_history(self, token_address, days=7):
        try:
            pool_info = self.solana_client.get_token_largest_accounts(token_address)
            if not pool_info.value:
                return []

            liquidity_history = []
            current_time = datetime.now()

            for pool in pool_info.value[:5]:
                pool_address = pool.address

                signatures = self.solana_client.get_signatures_for_address(
                    pool_address,
                    limit=100
                )

                if signatures.value:
                    for sig in signatures.value:
                        tx_time = datetime.fromtimestamp(sig.block_time)
                        if (current_time - tx_time).days > days:
                            continue

                        tx = self.solana_client.get_transaction(
                            Signature.from_string(sig.signature)
                        )

                        if tx.value:
                            liquidity_history.append({
                                'timestamp': sig.block_time,
                                'pool_address': str(pool_address),
                                'transaction': sig.signature,
                                'change': tx.value.meta.pre_token_balances if tx.value.meta else None
                            })

            return sorted(liquidity_history, key=lambda x: x['timestamp'])

        except Exception as e:
            logging.error(f"Error getting Solana liquidity history: {e}")
            return []

    def get_token_analytics(self, token_address):
        try:
            return {
                'daily_active_addresses': self.get_solana_daily_active_addresses(token_address),
                'holders_distribution': self.get_solana_token_holders_distribution(token_address),
                'liquidity_history': self.get_solana_token_liquidity_history(token_address)
            }

        except Exception as e:
            logging.error(f"Error getting token analytics: {e}")
            return {}
