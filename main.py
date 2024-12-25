from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.transaction_status import EncodedConfirmedTransactionWithStatusMeta
from telegram import Bot
import time
import json
import base64
import asyncio

TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
QUICKNODE_RPC_URL = ""
TARGET_WALLET = ""
THRESHOLD_AMOUNT = 1

bot = Bot(token=TELEGRAM_TOKEN)
solana_client = Client(QUICKNODE_RPC_URL)

async def check_solana_transactions():
    try:
        wallet_pubkey = Pubkey.from_string(TARGET_WALLET)
        response = solana_client.get_signatures_for_address(wallet_pubkey, limit=10)
        transactions = response.value

        if not transactions:
            print("No transactions found.")
            return

        for tx in transactions:
            tx_signature = tx.signature
            tx_details = solana_client.get_transaction(tx_signature)
            if not tx_details or not tx_details.value:
                continue

            parsed_tx = tx_details.value
            value = extract_transaction_value(parsed_tx)
            if value >= THRESHOLD_AMOUNT:
                message = (
                    f"🚨 LedgerEyeBot Alert！\n"
                    f"Wallet Address: {TARGET_WALLET}\n"
                    f"Trade Amount: {value} SOL\n"
                    f"Trade Hash: {tx_signature}\n"
                    f"Trade Detail: https://explorer.solana.com/tx/{tx_signature}"
                )

                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print(f"check_solana_transactions error: {e}")

def extract_transaction_value(transaction):
    value = 0
    try:
        if isinstance(transaction, EncodedConfirmedTransactionWithStatusMeta):
            tx_data = transaction.transaction

            tx_json_str = tx_data.to_json()
            tx_json = json.loads(tx_json_str)

            instructions = tx_json["transaction"]["message"]["instructions"]

            for instr in instructions:
                if instr["programIdIndex"] == 1:
                    lamports = decode_lamports(instr["data"])
                    value = max(value, lamports / 1e9)
    except Exception as e:
        print(f"extract_transaction_value error: {e}")
    return value;

def decode_lamports(data):
    decode_bytes = base64.b64decode(data)
    return int.from_bytes(decode_bytes, "big")

async def main():
    print("Launch LedgerEyeBot...")

    while True:
        await check_solana_transactions()
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())