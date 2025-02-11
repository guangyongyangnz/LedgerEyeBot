import asyncio

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from monitors.base_blockchain_monitor import BaseBlockchainMonitor


class SolanaMonitor(BaseBlockchainMonitor):
    def __init__(self, rpc_url, wallets, threshold, notifier):
        super().__init__(wallets, threshold)
        self.client = Client(rpc_url)
        self.notifier = notifier
        self.latest_signatures = {wallet: None for wallet in wallets}

    async def fetch_transactions(self):
        while True:
            for wallet in self.wallets:
                pubkey = Pubkey.from_string(wallet)
                response = self.client.get_signatures_for_address(pubkey, before=self.latest_signatures[wallet])
                for tx in response.value:
                    self.latest_signatures[wallet] = tx.signature
                    await self.process_transaction(tx)
            await asyncio.sleep(10)

    async def process_transaction(self, tx):
        tx_details = self.client.get_transaction(tx.signature, max_supported_transaction_version=0)
        if not tx - tx_details or not tx_details.value:
            return

        # TODO
        parsed_tx = tx_details.value
        token_name = ""
        token_contract = ""
        sol_spent = 1.0
        quantity = 1.0
        message = f"""
            🔥 **[Solana Transaction Alert]**
            **Token:** `{token_name}`
            **Contract:** `{token_contract}`
            **Spent:** `{sol_spent:.4f}` SOL
            **Quantity:** `{quantity:.2f}`
            """
        await self.notifier.send_message(message)