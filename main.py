import os
import requests
from flask import Flask, request

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# =========================
# TELEGRAM SEND MESSAGE
# =========================

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

# =========================
# WEBHOOK SETUP
# =========================

def set_webhook():
    url = f"{RENDER_URL}/webhook"
    requests.get(f"{BASE_URL}/setWebhook?url={url}")
    print("Webhook set to:", url)

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return "BOT RUNNING"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    print("🔥 UPDATE RECEIVED:", data)

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    print("MESSAGE:", text)

    # =========================
    # COMMANDS
    # =========================

    if text == "/START":
        send_message(chat_id, "🚀 Bot is LIVE")
        return "ok"

    if text == "LIVE":
        send_message(chat_id, "📊 LIVE SCAN WORKING")
        return "ok"

    if text == "RADAR TODAY":
        send_message(chat_id, "📡 RADAR SCAN ACTIVE")
        return "ok"

    if "BHEL" in text:
        send_message(chat_id, "📊 BHEL scan received")
        return "ok"

    if "RADAR" in text:
        send_message(chat_id, "📡 Radar request processed")
        return "ok"

    send_message(chat_id, f"Received: {text}")

    return "ok"

# =========================
# START SERVER
# =========================

if __name__ == "__main__":
    print("🚀 BOT STARTING...")

    set_webhook()

    app.run(host="0.0.0.0", port=PORT)
