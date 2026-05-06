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
from telegram import Bot
from flask import Flask

# ================= CONFIG =================
TOKEN = "8695622015:AAGQvyaYVoI6ZGZf4qt2D-pdXeFutLKNL80"
CHAT_ID = 309248606

bot = Bot(token=TOKEN)
app = Flask(__name__)

# ================= TELEGRAM =================
async def send_telegram(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        print("Telegram Error:", e)

# ================= STRATEGY =================
def check_conditions(df):
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

# ================= SCANNER =================
def scan_market():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)

    print(f"Scanning at {now.strftime('%H:%M:%S')}")

    FNO_STOCKS = [
        "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS",
        "INFY.NS","TCS.NS","LT.NS","AXISBANK.NS",
        "KOTAKBANK.NS","ADANIENT.NS","ADANIGREEN.NS"
    ]

    results = []

    for stock in FNO_STOCKS:
        try:
            df = yf.download(stock, interval="15m", period="5d", progress=False)

            if len(df) < 30:
                continue

            if check_conditions(df):
                results.append(stock)

        except Exception as e:
            print(stock, e)

    if results:
        msg = "🔥 15M BREAKOUT 🔥\n\n" + "\n".join(results)
        asyncio.run(send_telegram(msg))
    else:
        print("No setup")

# ================= SCHEDULER =================
def run_scheduler():
    start = datetime.datetime.strptime("09:31", "%H:%M")
    end = datetime.datetime.strptime("15:16", "%H:%M")

    while start <= end:
        schedule.every().day.at(start.strftime("%H:%M")).do(scan_market)
        start += datetime.timedelta(minutes=15)

    while True:
        schedule.run_pending()
        time.sleep(1)

# ================= FLASK SERVER =================
@app.route('/')
def home():
    return "Bot Running ✅"

# ================= START =================
if __name__ == "__main__":
    # run scheduler in background thread
    threading.Thread(target=run_scheduler).start()

    # start flask server (Render requirement)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
