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
MAX_WORKERS = 8

bot = Bot(token=TOKEN)
app = Flask(__name__)

# store last scan
last_scan = {}

# ================= TELEGRAM =================
async def send_telegram(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        print("Telegram Error:", e)

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

# ================= WORKER =================
def process_stock(stock):
    try:
        df = yf.download(stock, interval="15m", period="3d", progress=False)

        if len(df) < 30:
            return None, None

        if check_conditions(df):
            candle_time = df.index[-1].strftime("%H:%M")
            return stock.replace(".NS",""), candle_time

    except Exception as e:
        print(stock, e)

    return None, None

# ================= SCAN =================
def scan_market():
    global last_scan

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)

    scan_time = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    print(f"🔍 Scan at {scan_time}")

    FNO_STOCKS = [
        "RELIANCE.NS","SBIN.NS","BHEL.NS","HDFCBANK.NS",
        "ICICIBANK.NS","INFY.NS","TCS.NS","LT.NS"
    ]

    current_scan = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_stock, s) for s in FNO_STOCKS]

        for future in as_completed(futures):
            stock, candle = future.result()
            if stock:
                if candle not in current_scan:
                    current_scan[candle] = []
                current_scan[candle].append(stock)

    # ===== BUILD MESSAGE =====
    msg = f"📊 15M SCAN REPORT\n\n"
    msg += f"⏰ Scan Time: {scan_time}\n"
    msg += f"📅 Date: {date_str}\n\n"

    all_times = set(last_scan.keys()).union(set(current_scan.keys()))

    if not all_times:
        msg += "❌ NO STOCK\n"
    else:
        for t in sorted(all_times):
            stocks = current_scan.get(t, [])
            if stocks:
                msg += f"🕒 {t} → {', '.join(stocks)}\n"
            else:
                msg += f"🕒 {t} → NO STOCK\n"

    # update last scan
    last_scan = current_scan.copy()

    asyncio.run(send_telegram(msg))

# ================= SCHEDULER =================
def run_scheduler():
    print("🚀 Scheduler started")

    start = datetime.datetime.strptime("09:31", "%H:%M")
    end = datetime.datetime.strptime("15:16", "%H:%M")

    while start <= end:
        schedule.every().day.at(start.strftime("%H:%M")).do(scan_market)
        start += datetime.timedelta(minutes=15)

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

    asyncio.run(send_telegram("🚀 BOT STARTED"))

    # first scan immediately
    scan_market()

    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
