import requests
import base64
import struct

BOT_TOKEN = ""  # Your Bot Token
CHAT_ID = ""
MESSAGE = "Hello from LedgerEyeBot!"

def decode_instruction_data(transfer_data):
    try:
        # Base64 解码数据
        decoded = base64.b64decode(transfer_data + "=" * (-len(transfer_data) % 4))
        print(f"Decoded bytes: {[hex(b) for b in decoded]}")  # 打印解码后的字节

        # 检查解码结果
        if len(decoded) >= 9:
            instruction_type = decoded[0]
            print(f"Instruction type: {instruction_type}")

            if instruction_type == 2:  # 检查是否为 Transfer 指令
                lamports = struct.unpack("<Q", decoded[1:9])[0]
                print(f"Decoded lamports: {lamports}")
                return lamports

        print(f"Invalid instruction type or format: {decoded}")
        return 0
    except Exception as e:
        print(f"decode_transfer_amount error: {e}")
        return 0

def main():
    print("Launch LedgerEyeBot...")
    data = "3Bxs3zvFeZybcbU3"
    lamports = decode_instruction_data(data)
    print(f"Lamports: {lamports}")

if __name__ == "__main__":
    main()