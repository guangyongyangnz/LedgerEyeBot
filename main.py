from solana.rpc.api import Client
from solders.pubkey import Pubkey
from telegram import Bot
import json
import base64
import asyncio
import time
import struct

TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
SOLANA_RPC_URL = ""
# SPL token: Dc78ytMezDnQDUSAA9N6wE1fsUZ9LQaf8brVw5Eom2Vu
# second wallet:
TARGET_WALLET = "HfmBFDPvM2MZoSCjD2QvEdeJQLr64mKWPKkJSop8youD"
THRESHOLD_AMOUNT = 0.01

bot = Bot(token=TELEGRAM_TOKEN)
solana_client = Client(SOLANA_RPC_URL)

# Only focus on transaction records after the program is started
# start_time = int(time.time())
# Had deal with the processed signatures to prevent duplicate alarms
processed_transactions = set()

async def check_solana_transactions():
    try:
        wallet_pubkey = Pubkey.from_string(TARGET_WALLET)
        response = solana_client.get_signatures_for_address(wallet_pubkey, limit=5)
        transactions = response.value

        if not transactions:
            print("No transactions found.")
            return

        for tx in transactions:
            tx_signature = tx.signature
            tx_timestamp = tx.block_time

            # if tx_timestamp and tx_timestamp < start_time:
            #     continue

            if tx_signature in processed_transactions:
                print(f"Transaction {tx_signature} already processed, skipping")
                continue

            tx_details = solana_client.get_transaction(tx_signature)
            print(f"tx_details details: {tx_details}")
            if not tx_details or not tx_details.value:
                continue

            parsed_tx = tx_details.value
            result = extract_token_purchase(parsed_tx)
            print(f"Token purchase: {result}")
            if result:
                token_name, token_contract, sol_spent = result
                if sol_spent >= THRESHOLD_AMOUNT:
                    message = (
                        f"🚨 LedgerEyeBot Alert!\n"
                        f"Wallet: {TARGET_WALLET}\n"
                        f"Spent: {sol_spent:.2f} SOL\n"
                        f"Purchased: {token_name}\n"
                        f"Token Contract: {token_contract}\n"
                        f"Transaction Hash: {tx_signature}\n"
                    )

                    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                # Add to processed set
                processed_transactions.add(tx_signature)
    except Exception as e:
        print(f"check_solana_transactions error: {e}")

def extract_token_purchase(transaction):
    try:
        tx_json = json.loads(transaction.transaction.to_json())
        meta = tx_json["meta"]
        message = tx_json["transaction"]["message"]

        pre_balances = meta["pre_balances"]
        post_balance = meta["post_balances"]
        sol_spent = (pre_balances[0] - post_balance[0]) / 1_000_000_000

        instructions = message["instructions"]
        for instruction in instructions:
            program_id_index = instruction["programIdIndex"]
            program_id = message["accountKeys"][program_id_index]

            if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                token_account_index = instruction["accounts"][-1]
                token_contract_index = instruction["accounts"][0]
                token_account = message["accountKeys"][token_account_index]
                token_contract = message["accountKeys"][token_contract_index]

                token_name = get_token_name(token_contract)
                return token_name, token_contract, sol_spent
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

def decode_transfer_amount(transfer_data):
    try:
        decoded = base64.b64decode(transfer_data + "=" * (-len(transfer_data) % 4))
        print(f"Decoded bytes: {decoded}")

        if len(decoded) >= 9 and decoded[0] == 3:
            amount = struct.unpack("<Q", decoded[1:9])[0]
            print(f"Decoded transfer amount: {amount}")
            return amount

        print(f"Invalid transfer instruction format: {decoded}")
        return 0
    except Exception as e:
        print(f"decode_transfer_amount error: {e}")
        return 0


def extract_transaction_value(transaction):
    print(f"Transaction: {transaction}")
    try:
        tx_json = json.loads(transaction.transaction.to_json())
        meta = tx_json["meta"]
        message = tx_json["transaction"]["message"]
        accounts = message["accountKeys"]
        # print log for debug
        print(f"Accounts: {accounts}")
        print(f"Pre balances: {meta['preBalances']}")
        print(f"Post balances: {meta['postBalances']}")

        for instruction in message["instructions"]:
            if instruction["programIdIndex"] == 2:
                from_index = instruction["accounts"][0]
                to_index = instruction["accounts"][1]

                from_account = accounts[from_index]
                to_account = accounts[to_index]

                print(f"From account: {from_account}")
                print(f"To account: {to_account}")

                if from_account == TARGET_WALLET:
                    pre_balance = meta["preBalances"][from_index]
                    post_balance = meta["postBalances"][from_index]

                    lamports = pre_balance - post_balance - meta["fee"]
                    if lamports > 0:
                        sol_amount = lamports / 1_000_000_000
                        print(f"Extracted amount based on balance change: {sol_amount} SOL")
                        return sol_amount

        return 0
    except Exception as e:
        print(f"extract_transaction_value error: {e}")
        return 0

async def main():
    print("Launch LedgerEyeBot...")

    while True:
        await check_solana_transactions()
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())