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
        print("📤 Sending message...")
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("✅ Message sent")
    except Exception as e:
        print("❌ Telegram Error:", e)

# ================= STRATEGY =================
def check_conditions(df):
    try:
        df = df.copy()

        df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close'])/3).cumsum() / df['Volume'].cumsum()
        df['vol_sma20'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]

        cond1 = last['Volume'] > 500000
        cond2 = (last['Close'] * last['Volume']) > 150000000
        cond3 = ((last['High'] - last['Low']) / last['Open'] * 100) > 1
        cond4 = (abs(last['Close'] - last['Open']) / last['Open'] * 100) > 0.6
        cond5 = last['Close'] > last['vwap']
        cond6 = last['Volume'] > (last['vol_sma20'] * 2)
        cond7 = last['Close'] > last['Open']

        return all([cond1, cond2, cond3, cond4, cond5, cond6, cond7])

    except Exception as e:
        print("Condition error:", e)
        return False

# ================= WORKER =================
def process_stock(stock):
    try:
        df = yf.download(stock, interval="15m", period="3d", progress=False)

        if len(df) < 30:
            return None

        if check_conditions(df):
            return stock

    except Exception as e:
        print(stock, e)

    return None

# ================= SCAN =================
def scan_market():
    print("🔍 Running scan...")

    FNO_STOCKS = ["RELIANCE.NS","SBIN.NS","BHEL.NS"]

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_stock, s) for s in FNO_STOCKS]

        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    now = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M")

    if results:
        msg = f"⏰ {now}\n✅ STOCKS:\n" + "\n".join(results)
    else:
        msg = f"⏰ {now}\n❌ NO STOCK"

    asyncio.run(send_telegram(msg))

# ================= SCHEDULER =================
def run_scheduler():
    print("🚀 Scheduler started")

    # DEBUG: run every 1 minute
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

    # start scheduler thread
    threading.Thread(target=run_scheduler, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
