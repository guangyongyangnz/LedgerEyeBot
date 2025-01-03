from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.signature import Signature
from telegram import Bot
import json
import base64
import asyncio
import time
from collections import defaultdict
from solana.rpc.types import TxOpts

TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
# SOLANA_RPC_URL = ""
SOLANA_RPC_URL = ""

bot = Bot(token=TELEGRAM_TOKEN)
solana_client = Client(SOLANA_RPC_URL)

TARGET_WALLET = ["64ebCdMzJ1K33ATzVwaPNuNgPfXrAy7gocutsY8jMCVm"]
THRESHOLD_AMOUNT = 0.01
# seconds
FOMO_INTERVAL = 15 * 60
start_time = int(time.time())

fomo_cache = defaultdict(lambda: {
    "token_contract": "",
    "total_sol_spent": 0.0,
    "transactions": []
})


async def check_solana_transactions(wallet):
    try:
        # Had deal with the processed signatures to prevent duplicate alarms
        processed_transactions = set()

        wallet_pubkey = Pubkey.from_string(wallet)
        while True:
            response = solana_client.get_signatures_for_address(wallet_pubkey, limit=5)
            transactions = response.value
            if not transactions:
                print(f"No transactions found. wallet: {wallet}")
                return

            for tx in transactions:
                tx_signature = tx.signature
                if tx_signature in processed_transactions:
                    continue

                print("1")
                try:
                    tx_details = solana_client.get_transaction(tx_signature,
                                                               max_supported_transaction_version=0)
                    print("1.5")
                except Exception as get_tx_error:
                    print(f"Error fetching transaction: {get_tx_error}")
                    continue

                print("2")
                if not tx_details or not tx_details.value:
                    print("3")
                    continue

                print("4")
                parsed_tx = tx_details.value
                result = extract_token_purchase(parsed_tx)
                print(f"Token purchase: {result}")

                if result:
                    token_name, token_contract, sol_spent = result
                    if sol_spent >= THRESHOLD_AMOUNT:
                        if token_name in fomo_cache:
                            fomo_cache[token_name]["total_sol_spent"] += sol_spent
                            fomo_cache[token_name]["transactions"].append({
                                "wallet": wallet,
                                "sol_spent": sol_spent,
                                "quantity": 0
                            })
                        else:
                            fomo_cache[token_name] = {
                                "token_contract": token_contract,
                                "total_sol_spent": sol_spent,
                                "transactions": [{
                                    "wallet": wallet,
                                    "sol_spent": sol_spent,
                                    "quantity": 0
                                }]
                            }

                processed_transactions.add(tx_signature)
            await asyncio.sleep(10)
    except Exception as e:
        print(f"check_solana_transactions error for wallet {wallet}: {e}")


async def monitor_fomo():
    while True:
        try:
            if fomo_cache:
                await  process_fomo_signals()
            await asyncio.sleep(FOMO_INTERVAL)
        except Exception as e:
            print(f"monitor_fomo error: {e}")


async def process_fomo_signals():
    try:
        for token_name, data in fomo_cache.items():
            token_contract = data["token_contract"]
            total_sol_spent = data["total_sol_spent"]
            transactions = data["transactions"]

            message = f"[FOMO Single] ${token_name} ({len(transactions)} Smart Wallet Purchase)\n\n"
            message += f"Contract Address: {token_contract}\n\n"

            for tx in transactions:
                message += f"🟢Wallet{tx['wallet']} Spent {tx['sol_spent']} SOL Purchase {tx['quantity']:.2f} {token_name}\n"

            message += f"\n Total Spent: {total_sol_spent:.2f} SOL\n"
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        fomo_cache.clear()
    except Exception as e:
        print(f"process_fomo_signals error: {e}")


def extract_token_purchase(transaction):
    try:
        tx_json = json.loads(transaction.transaction.to_json())
        meta = tx_json.get("meta")
        if not meta:
            print("No meta data.")
            return None

        pre_balances = meta.get("preBalances")
        post_balance = meta.get("postBalances")
        if not pre_balances or not post_balance:
            print("Balance information missing in meta")
            return None

        sol_spent = (pre_balances[0] - post_balance[0]) / 1_000_000_000
        message = tx_json["transaction"]["message"]
        instructions = message["instructions"]
        for instruction in instructions:
            program_id_index = instruction["programIdIndex"]
            program_id = message["accountKeys"][program_id_index]

            # detect SPL Token transaction
            if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                token_account_index = instruction["accounts"][-1]
                token_contract_index = instruction["accounts"][0]
                token_account = message["accountKeys"][token_account_index]
                token_contract = message["accountKeys"][token_contract_index]

                token_name = get_token_name(token_contract)
                return token_name, token_contract, sol_spent
        print("No SPL Token purchase found in transaction.")
        return None
    except Exception as e:
        print(f"extract_token_purchase error: {e}")
        return None


def get_token_name(token_contract):
    try:
        metadata_pubkey = get_metadata_account(token_contract)
        response = solana_client.get_account_info(metadata_pubkey)

        if not response["result"]["value"]:
            return "Unknown Token"

        account_data = response["result"]["value"]["data"][0]
        decoded_data = base64.b64decode(account_data)

        name_start = 32
        name_length = 32
        token_name = decoded_data[name_start: name_start + name_length].decode("utf-8").rstrip("\x00")
        return token_name
    except Exception as e:
        print(f"get_token_name error: {e}")
        return "Unknown Token"


def get_metadata_account(token_contract):
    try:
        TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # SPL Token Metadata Program ID
        mint_pubkey = Pubkey.from_string(token_contract)
        metadata_seeds = [
            b"metadata",
            bytes(Pubkey.from_string(TOKEN_METADATA_PROGRAM_ID)),
            bytes(mint_pubkey),
        ]
        metadata_pubkey = Pubkey.create_program_address(metadata_seeds, TOKEN_METADATA_PROGRAM_ID)
        return metadata_pubkey
    except Exception as e:
        print(f"get_metadata_account error: {e}")
        return None


async def main():
    print("Launch LedgerEyeBot...")

    await asyncio.gather(*[check_solana_transactions(wallet) for wallet in TARGET_WALLET], monitor_fomo())


if __name__ == "__main__":
    asyncio.run(main())
