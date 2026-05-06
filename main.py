import yfinance as yf
import pandas as pd
import numpy as np
import schedule
import time
import datetime
import pytz
import asyncio
import threading
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram import Bot
from flask import Flask

# ================= CONFIG =================
TOKEN = "8695622015:AAGQvyaYVoI6ZGZf4qt2D-pdXeFutLKNL80"
CHAT_ID = 309248606
MAX_WORKERS = 5

bot = Bot(token=TOKEN)
app = Flask(__name__)

# ================= TELEGRAM =================
async def send_telegram(msg):
    try:
        print("📤 Sending:", msg)
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("✅ Sent")
    except Exception as e:
        print("❌ Telegram Error:", e)

# ================= STRATEGY =================
def check_conditions(df):
    try:
        df = df.copy()

        df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close'])/3).cumsum() / df['Volume'].cumsum()
        df['vol_sma20'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]

        return (
            last['Volume'] > 500000 and
            (last['Close'] * last['Volume']) > 150000000 and
            ((last['High'] - last['Low']) / last['Open'] * 100) > 1 and
            (abs(last['Close'] - last['Open']) / last['Open'] * 100) > 0.6 and
            last['Close'] > last['vwap'] and
            last['Volume'] > (last['vol_sma20'] * 2) and
            last['Close'] > last['Open']
        )
    except:
        return False

# ================= SCAN =================
def scan_market():
    print("🔍 Running scan...")

    FNO_STOCKS = ["RELIANCE.NS","SBIN.NS","BHEL.NS"]

    results = []

    for stock in FNO_STOCKS:
        try:
            df = yf.download(stock, interval="15m", period="3d", progress=False)

            if len(df) < 30:
                continue

            if check_conditions(df):
                results.append(stock)

        except Exception as e:
            print(stock, e)

    now = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M")

    if results:
        msg = f"⏰ {now}\n✅ STOCKS:\n" + "\n".join(results)
    else:
        msg = f"⏰ {now}\n❌ NO STOCK"

    asyncio.run(send_telegram(msg))

# ================= SCHEDULER =================
def run_scheduler():
    print("🚀 Scheduler started")

    # DEBUG MODE (every 1 min)
    schedule.every(1).minutes.do(scan_market)

    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= FLASK =================
@app.route('/')
def home():
    return "Bot Running ✅"

# ================= MAIN =================
if __name__ == "__main__":
    print("🔥 Bot Starting...")

    # send startup message
    asyncio.run(send_telegram("🚀 BOT STARTED"))

    # FORCE FIRST SCAN (important fix)
    scan_market()

    # start scheduler properly
    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()

    # run flask
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
