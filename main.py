from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.transaction_status import EncodedConfirmedTransactionWithStatusMeta
from telegram import Bot
import json
import base64
import asyncio
import time
import struct

TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
QUICKNODE_RPC_URL = ""
# second wallet: 8LYBwhJqiDf64EHPWASJdgnXy51HKuXawoavAJ3HGQb9
TARGET_WALLET = "64ebCdMzJ1K33ATzVwaPNuNgPfXrAy7gocutsY8jMCVm"
THRESHOLD_AMOUNT = 1

bot = Bot(token=TELEGRAM_TOKEN)
solana_client = Client(QUICKNODE_RPC_URL)

# Only focus on transaction records after the program is started
start_time = int(time.time())
# Had deal with the processed signatures to prevent duplicate alarms
processed_transactions = set()

async def check_solana_transactions():
    try:
        wallet_pubkey = Pubkey.from_string(TARGET_WALLET)
        # 5 transactions can be queried each time
        response = solana_client.get_signatures_for_address(wallet_pubkey, limit=5)
        transactions = response.value

        if not transactions:
            print("No transactions found.")
            return

        for tx in transactions:
            tx_signature = tx.signature
            # Only focus on latest transaction
            tx_timestamp = tx.block_time
            if tx_timestamp and tx_timestamp < start_time:
                continue

            if tx_signature in processed_transactions:
                print(f"Transaction {tx_signature} already processed, skipping")
                continue

            tx_details = solana_client.get_transaction(tx_signature)
            print(f"tx_details details: {tx_details}")
            if not tx_details or not tx_details.value:
                continue

            parsed_tx = tx_details.value
            value = extract_transaction_value(parsed_tx)
            print(f"Transaction amount: {value} SOL")
            if value >= THRESHOLD_AMOUNT:
                message = (
                    f"🚨 LedgerEyeBot Alert！\n"
                    f"Wallet Address: {TARGET_WALLET}\n"
                    f"Trade Amount: {value:.4f} SOL\n"
                    f"Trade Hash: {tx_signature}\n"
                    f"Trade Detail: https://explorer.solana.com/tx/{tx_signature}"
                )

                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                # Add to processed set
                processed_transactions.add(tx_signature)
    except Exception as e:
        print(f"check_solana_transactions error: {e}")

def extract_transaction_value(transaction):
    print(f"Transaction: {transaction}")
    try:
        tx_json = json.loads(transaction.transaction.to_json())
        meta = tx_json["meta"]
        message = tx_json["transaction"]["message"]
        accounts = message["accountKeys"]
        # 打印账户和余额信息
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


        # tx_json = json.loads(transaction.transaction.to_json())
        # message = tx_json["transaction"]["message"]
        #
        # accounts = message["accountKeys"]
        # instructions = message["instructions"]
        #
        # for instruction in instructions:
        #     if instruction["programIdIndex"] == 2:
        #         from_index = instruction["accounts"][0]
        #         to_index = instruction["accounts"][1]
        #         from_account = accounts[from_index]
        #         to_account = accounts[to_index]
        #
        #         print(f"From account: {from_account}")
        #         print(f"To account: {to_account}")
        #
        #         if from_account == TARGET_WALLET:
        #             transfer_data = instruction["data"]
        #             lamports = decode_transfer_amount(transfer_data)
        #             print(f"Lamports: {lamports}")
        #             return lamports / 1000000000
        #
        # return 0
    except Exception as e:
        print(f"extract_transaction_value error: {e}")
        return 0

def decode_transfer_amount(transfer_data):
    try:
        decoded = base64.b64decode(transfer_data + "=" * (-len(transfer_data) % 4))
        if len(decoded) >= 9 and decoded[0] == 2:
            amount = struct.unpack("<Q", decoded[1:9])[0]
            return amount

        print(f"Invalid instruction type: {decoded[0] if decoded else 'no data'}")
        return 0
    except Exception as e:
        print(f"decode_transfer_amount error: {e}")
        return 0

async def main():
    print("Launch LedgerEyeBot...")

    while True:
        await check_solana_transactions()
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())