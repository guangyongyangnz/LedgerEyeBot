import Notifier
import EthereumMonitor
import SolanaMonitor
import TaskManager
import DexScreenerMonitor

import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
ETHEREUM_RPC_URL = os.getenv("ETHEREUM_RPC_URL")

TARGET_ETH_WALLETS = ["0xYourEthWallet1", "0xYourEthWallet2"]
TARGET_SOL_WALLETS = ["YourSolWallet1", "YourSolWallet2"]
THRESHOLD_AMOUNT = 1
DEX_CHECK_INTERVAL = 600

notifier = Notifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
task_manager = TaskManager()

eth_monitor = EthereumMonitor(
    rpc_url=ETHEREUM_RPC_URL,
    wallets=TARGET_ETH_WALLETS,
    threshold=THRESHOLD_AMOUNT,
    notifier=notifier
)
task_manager.add_task(eth_monitor.fetch_transactions())

sol_monitor = SolanaMonitor(
    rpc_url=SOLANA_RPC_URL,
    wallets=TARGET_SOL_WALLETS,
    threshold=THRESHOLD_AMOUNT,
    notifier=notifier
)
task_manager.add_task(sol_monitor.fetch_transactions())

dex_monitor = DexScreenerMonitor(telegram_token=TELEGRAM_TOKEN, chat_id=TELEGRAM_CHAT_ID)
task_manager.add_task(dex_monitor.monitor_trending(interval=DEX_CHECK_INTERVAL))

# Run all tasks
if __name__ == "__main__":
    print("Starting Multi-Chain Monitor...")
    asyncio.run(task_manager.run_all())
