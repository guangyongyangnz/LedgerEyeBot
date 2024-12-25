import requests

BOT_TOKEN = ""  # Your Bot Token
CHAT_ID = ""
MESSAGE = "Hello from LedgerEyeBot!"

# 发送消息
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": MESSAGE
}
response = requests.post(url, json=payload)
print(response.json())
