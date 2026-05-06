import yfinance as yf
import pandas as pd
import numpy as np
import schedule
import time
import datetime
import pytz
from telegram import Bot

# ================= CONFIG =================
TOKEN = "8695622015:AAGQvyaYVoI6ZGZf4qt2D-pdXeFutLKNL80"
CHAT_ID = "309248606"

bot = Bot(token=TOKEN)

# NSE FNO STOCK LIST (sample - you can expand)
FNO_STOCKS = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","INFY.NS",
    "TCS.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS","ADANIENT.NS",
    "ADANIGREEN.NS","BAJFINANCE.NS","MARUTI.NS","TITAN.NS"
]

# ============== STRATEGY ==================

def check_conditions(df):
    try:
        df = df.copy()

        df['vwap'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close'])/3).cumsum() / df['Volume'].cumsum()
        df['vol_sma20'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]

        # CONDITIONS (from your image)
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


# ============== SCANNER ==================

def scan_market():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist)

    print(f"Scanning at {now}")

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
        msg = "🔥 15M BREAKOUT SCAN 🔥\n\n"
        msg += "\n".join(results)

        bot.send_message(chat_id=CHAT_ID, text=msg)
        print("Alert sent")

    else:
        print("No setup")


# ============== SCHEDULER ==================

def run_scheduler():
    times = []

    start = datetime.datetime.strptime("09:31", "%H:%M")
    end = datetime.datetime.strptime("15:16", "%H:%M")

    while start <= end:
        times.append(start.strftime("%H:%M"))
        start += datetime.timedelta(minutes=15)

    for t in times:
        schedule.every().day.at(t).do(scan_market)

    print("Scheduler Started")

    while True:
        schedule.run_pending()
        time.sleep(1)


# ============== START ==================

if __name__ == "__main__":
    run_scheduler()
