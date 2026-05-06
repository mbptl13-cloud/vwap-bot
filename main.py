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

# store last scan result
scan_history = []

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

        cond1 = last['Volume'] > 500000
        cond2 = (last['Close'] * last['Volume']) > 150000000
        cond3 = ((last['High'] - last['Low']) / last['Open'] * 100) > 1
        cond4 = (abs(last['Close'] - last['Open']) / last['Open'] * 100) > 0.6
        cond5 = last['Close'] > last['vwap']
        cond6 = last['Volume'] > (last['vol_sma20'] * 2)
        cond7 = last['Close'] > last['Open']

        return all([cond1, cond2, cond3, cond4, cond5, cond6, cond7])

    except:
        return False

# ================= WORKER =================
def process_stock(stock):
    try:
        df = yf.download(stock, interval="15m", period="3d", progress=False)

        if len(df) < 30:
            return None, None

        if check_conditions(df):
            last_time = df.index[-1].strftime("%H:%M")
            return stock, last_time

    except Exception as e:
        print(stock, e)

    return None, None

# ================= SCAN =================
def scan_market():
    global scan_history

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)

    scan_time = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")

    print(f"\n⚡ Scan at {scan_time}")

    FNO_STOCKS = [
        "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS",
        "INFY.NS","TCS.NS","LT.NS","AXISBANK.NS",
        "KOTAKBANK.NS","ADANIENT.NS","ADANIGREEN.NS",
        "BAJFINANCE.NS","MARUTI.NS","TITAN.NS","BHEL.NS"
    ]

    candle_map = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_stock, stock) for stock in FNO_STOCKS]

        for future in as_completed(futures):
            stock, candle_time = future.result()
            if stock:
                if candle_time not in candle_map:
                    candle_map[candle_time] = []
                candle_map[candle_time].append(stock.replace(".NS",""))

    # build message
    msg = f"📊 15M SCAN REPORT\n\n"
    msg += f"⏰ Scan Time: {scan_time}\n"
    msg += f"📅 Date: {date_str}\n\n"

    if candle_map:
        for t in sorted(candle_map.keys()):
            stocks = ", ".join(candle_map[t])
            msg += f"🕒 Candle {t} → {stocks}\n"
    else:
        msg += "❌ NO STOCK\n"

    # store history (last 2 scans)
    scan_history.append(msg)
    if len(scan_history) > 2:
        scan_history.pop(0)

    # send last 2 scans together
    final_msg = "\n\n".join(scan_history)

    asyncio.run(send_telegram(final_msg))

# ================= SCHEDULER =================
def run_scheduler():
    start = datetime.datetime.strptime("09:31", "%H:%M")
    end = datetime.datetime.strptime("15:16", "%H:%M")

    while start <= end:
        schedule.every().day.at(start.strftime("%H:%M")).do(scan_market)
        start += datetime.timedelta(minutes=15)

    print("🚀 Scheduler Started")

    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= FLASK =================
@app.route('/')
def home():
    return "Bot Running ✅"

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(target=run_scheduler).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
