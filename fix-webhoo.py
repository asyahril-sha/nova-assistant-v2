# fix_webhook.py
import requests
import time

TOKEN = "8740988219:AAFfgW6Cw23L5dzM9bBZLg6FyXrplb87yHQ"

print("1. Menghapus webhook...")
response = requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=True")
print("   Response:", response.json())

time.sleep(1)

print("\n2. Memastikan webhook sudah dihapus...")
response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
print("   Webhook info:", response.json())

print("\n3. Mencoba getUpdates untuk test...")
response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates")
print("   Pending updates:", response.json())
