from utils.Notifier import Notifier
from utils.TaskManager import TaskManager
from monitors.EthereumMonitor import EthereumMonitor
from monitors.SolanaMonitor import SolanaMonitor
from monitors.DexScreenerMonitor import DexScreenerMonitor

import os
import sys
from dotenv import load_dotenv
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL")
ETHEREUM_RPC_URL = os.getenv("ETHEREUM_RPC_URL")

TARGET_ETH_WALLETS = ["5ntZqUP1qF36hZc9sccq9ogKWmGyA9cp1YyPedZXsPdB", "5BiPQBP7P5F1JAarb4FDfUPBEXesfNVKYFKgTw3re9FB", "77D6ZCgfgpfNTT9hs8wapJiwU12eqgECBXFgarcbZpRY"]
TARGET_SOL_WALLETS = ["YourSolWallet1", "YourSolWallet2"]
THRESHOLD_AMOUNT = 1
DEX_CHECK_INTERVAL = 600

notifier = Notifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
task_manager = TaskManager()

# eth_monitor = EthereumMonitor(
#     rpc_url=ETHEREUM_RPC_URL,
#     wallets=TARGET_ETH_WALLETS,
#     threshold=THRESHOLD_AMOUNT,
#     notifier=notifier
# )
# task_manager.add_task(eth_monitor.fetch_transactions())
#
# sol_monitor = SolanaMonitor(
#     rpc_url=SOLANA_RPC_URL,
#     wallets=TARGET_SOL_WALLETS,
#     threshold=THRESHOLD_AMOUNT,
#     notifier=notifier
# )
# task_manager.add_task(sol_monitor.fetch_transactions())

dex_monitor = DexScreenerMonitor(notifier)
task_manager.add_task(dex_monitor.monitor_tokens())

# Run all tasks
if __name__ == "__main__":
    print("Starting Multi-Chain Monitor...")
    asyncio.run(task_manager.run_all())
