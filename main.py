from solana.rpc.api import Client
from solders.pubkey import Pubkey
from telegram import Bot
import time
import os
import requests

TELEGRAM_TOKEN = "" # Your Bot token
TELEGRAM_CHAT_ID = "" # Your chatId, obtain from telegram
QUICKNODE_RPC_URL = "" # RPC Provider URL
TARGET_WALLET = "" # Smart wallet
THRESHOLD_AMOUNT = 10

bot = Bot(token=TELEGRAM_TOKEN)
solana_client = Client(QUICKNODE_RPC_URL)

def check_solana_transactions():
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

                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print(f"check_solana_transactions error: {e}")

def extract_transaction_value(transaction):
    value = 0
    try:
        instructions = transaction.transaction.message.instructions
        for instr in instructions:
            if instr.program_id.to_string() == "11111111111111111111111111111111":
                if hasattr(instr, "parsed") and hasattr(instr.parsed, "info"):
                    info = instr.parsed.info
                    if "lamports" in info:
                        lamports = int(info["lamports"])
                        value = max(value, lamports / 1e9)
    except Exception as e:
        print(f"extract_transaction_value error: {e}")
    return value;

def main():
    print("Launch LedgerEyeBot...")

    while True:
        check_solana_transactions()
        time.sleep(30)

if __name__ == "__main__":
    main()