from dotenv import load_dotenv
import os

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from telegram import Bot
import json
import base64
import asyncio
import time
from collections import defaultdict

# load configuration
load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL")

print(f"Telegram Token: {TELEGRAM_TOKEN}")
print(f"Telegram Chat ID: {TELEGRAM_CHAT_ID}")
print(f"Solana RPC URL: {SOLANA_RPC_URL}")

bot = Bot(token=TELEGRAM_TOKEN)
solana_client = Client(SOLANA_RPC_URL)

TARGET_WALLET = ["5ntZqUP1qF36hZc9sccq9ogKWmGyA9cp1YyPedZXsPdB", "5BiPQBP7P5F1JAarb4FDfUPBEXesfNVKYFKgTw3re9FB", "77D6ZCgfgpfNTT9hs8wapJiwU12eqgECBXFgarcbZpRY"]
THRESHOLD_AMOUNT = 1
# seconds
FOMO_INTERVAL = 15 * 60
# the latest signature
latest_signatures = {wallet: None for wallet in TARGET_WALLET}

fomo_cache = defaultdict(lambda: {
    "token_contract": "",
    "total_sol_spent": 0.0,
    "transactions": []
})


async def check_solana_transactions(wallet):
    try:
        wallet_pubkey = Pubkey.from_string(wallet)
        global latest_signatures

        while True:
            response = solana_client.get_signatures_for_address(wallet_pubkey, before=latest_signatures[wallet])
            transactions = response.value
            if not transactions:
                print(f"No transactions found. wallet: {wallet}")
                await asyncio.sleep(10)
                return

            latest_signatures[wallet] = transactions[0].signature

            for tx in transactions:
                tx_signature = tx.signature
                print(f"tx_signature: {tx_signature}")

                tx_details = solana_client.get_transaction(tx_signature,
                                                           max_supported_transaction_version=0)
                if not tx_details or not tx_details.value:
                    continue

                parsed_tx = tx_details.value
                result = extract_token_purchase(parsed_tx)

                if result:
                    print(f"Token purchase: {result}")
                    token_name, token_contract, sol_spent, quantity = result
                    if token_name in fomo_cache:
                        fomo_cache[token_name]["total_sol_spent"] += sol_spent
                        fomo_cache[token_name]["transactions"].append({
                            "wallet": wallet,
                            "sol_spent": sol_spent,
                            "quantity": quantity
                        })
                    else:
                        fomo_cache[token_name] = {
                            "token_contract": token_contract,
                            "total_sol_spent": sol_spent,
                            "transactions": [{
                                "wallet": wallet,
                                "sol_spent": sol_spent,
                                "quantity": quantity
                            }]
                        }

            await asyncio.sleep(10)
    except Exception as e:
        print(f"check_solana_transactions error for wallet {wallet}: {e}")


async def monitor_fomo():
    while True:
        try:
            if fomo_cache:
                await process_fomo_signals()
            await asyncio.sleep(FOMO_INTERVAL)
        except Exception as e:
            print(f"monitor_fomo error: {e}")


async def process_fomo_signals():
    try:
        for token_name, data in fomo_cache.items():
            token_contract = data["token_contract"]
            total_sol_spent = data["total_sol_spent"]
            transactions = data["transactions"]

            # message = "-------------------------------------\n\n"
            message = f"🔥 **[FOMO Single]** ${token_name} ({len(transactions)} Smart Wallet Purchase)\n\n"
            message += f"**Contract Address:** `{token_contract}`\n\n"

            for tx in transactions:
                wallet = tx['wallet']
                sol_spent = tx['sol_spent']
                quantity = tx['quantity']
                message += f"🟢 **Wallet:** `{wallet}`\n"
                message += f"**Spent:** `{sol_spent:.9f}` SOL\n"
                message += f"**Purchase:** `{quantity:.2f}` {token_name}\n\n"

            message += f"**Total Spent:** `{total_sol_spent:.2f}` SOL\n"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
        fomo_cache.clear()
    except Exception as e:
        print(f"process_fomo_signals error: {e}")


def extract_token_purchase(transaction):
    try:
        tx_json = json.loads(transaction.transaction.to_json())
        meta = tx_json.get("meta")
        if not meta:
            return None

        pre_token_balances = meta.get("preTokenBalances")
        post_token_balance = meta.get("postTokenBalances")
        if not pre_token_balances or not post_token_balance:
            return None

        for pre_balance, post_balance in zip(pre_token_balances, post_token_balance):
            if pre_balance["mint"] != post_balance["mint"] or pre_balance["mint"] == "So11111111111111111111111111111111111111112":
                continue

            pre_amount = int(pre_balance["uiTokenAmount"]["amount"])
            post_amount = int(post_balance["uiTokenAmount"]["amount"])
            token_contract = pre_balance["mint"]
            sol_spent = (meta["preBalances"][0] - meta["postBalances"][0]) / 1_000_000_000
            # Only focus on Buy transaction
            if post_amount > pre_amount and sol_spent >= THRESHOLD_AMOUNT:
                token_name = get_token_name(token_contract)
                quantity = (post_amount - pre_amount) / (10 ** post_balance["uiTokenAmount"]["decimals"])
                return token_name, token_contract, sol_spent, quantity

        return None
    except Exception as e:
        print(f"extract_token_purchase error: {e}")
        return None


def get_token_name(token_contract):
    try:
        metadata_pubkey = get_metadata_account(token_contract)
        response = solana_client.get_account_info(metadata_pubkey)

        if not response.value or not response.value.data:
            return "Unknown Token"

        account_data = base64.b64decode(response.value.data[0])
        name_start = 32
        name_length = 32
        token_name = account_data[name_start: name_start + name_length].decode("utf-8").rstrip("\x00")
        return token_name
    except Exception as e:
        print(f"get_token_name error: {e}")
        return "Unknown Token"


def get_metadata_account(token_contract):
    try:
        if token_contract == "So11111111111111111111111111111111111111112":
            return None

        TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # SPL Token Metadata Program ID
        metadata_program_pubkey = Pubkey.from_string(TOKEN_METADATA_PROGRAM_ID)
        mint_pubkey = Pubkey.from_string(token_contract)
        metadata_seeds = [
            b"metadata",
            bytes(metadata_program_pubkey),
            bytes(mint_pubkey),
        ]
        metadata_pubkey = Pubkey.create_program_address(metadata_seeds, metadata_program_pubkey)
        return metadata_pubkey
    except Exception as e:
        print(f"get_metadata_account error: {e}")
        return None


async def main():
    print("Launch LedgerEyeBot...")

    await asyncio.gather(*[check_solana_transactions(wallet) for wallet in TARGET_WALLET], monitor_fomo())


if __name__ == "__main__":
    asyncio.run(main())
