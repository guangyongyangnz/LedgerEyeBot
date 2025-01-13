from abc import ABC, abstractmethod


class BaseBlockchainMonitor(ABC):
    def __init__(self, wallets, threshold):
        self.wallets = wallets
        self.threshold = threshold

    @abstractmethod
    async def fetch_transactions(self):
        pass

    async def process_transactions(self, transaction):
        pass
