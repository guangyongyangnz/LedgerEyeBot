import asyncio

from web3 import Web3
import BaseBlockchainMonitor


class EthereumMonitor(BaseBlockchainMonitor):
    def __init__(self, rpc_url, wallets, threshold, notifier):
        super().__init__(wallets, threshold)
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.notifier = notifier
        self.latest_block = self.web3.eth.block_number

    async def fetch_transactions(self):
        while True:
            current_block = self.web3.eth.block_number
            for block_number in range(self.latest_block + 1, current_block + 1):
                block = self.web3.eth.get_block(block_number, full_transactions=True)
                for tx in block.transactions:
                    if tx.to and tx.to.lower() in [w.lower() for w in self.wallets]:
                        await self.process_transaction(tx)
                self.latest_block = block_number
            await asyncio.sleep(10)

    async def process_transaction(self, tx):
        value_in_ether = self.web3.fromWei(tx.value, 'ether')
        if value_in_ether >= self.threshold:
            message = f"""
            🔥 **[Ethereum Transaction Alert]**
            **From:** `{tx['from']}`
            **To:** `{tx.to}`
            **Value:** `{value_in_ether:.4f}` ETH
            **Tx Hash:** `{tx.hash.hex()}`
            """
            await self.notifier.send_notification(message)
