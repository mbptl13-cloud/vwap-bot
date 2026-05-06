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
    "360ONE.NS",
    "ABB.NS",
    "APLAPOLLO.NS",
    "AUBANK.NS",
    "ADANIENSOL.NS",
    "ADANIENT.NS",
    "ADANIGREEN.NS",
    "ADANIPORTS.NS",
    "ADANIPOWER.NS",
    "ABCAPITAL.NS",
    "ALKEM.NS",
    "AMBER.NS",
    "AMBUJACEM.NS",
    "ANGELONE.NS",
    "APOLLOHOSP.NS",
    "ASHOKLEY.NS",
    "ASIANPAINT.NS",
    "ASTRAL.NS",
    "AUROPHARMA.NS",
    "DMART.NS",
    "AXISBANK.NS",
    "BSE.NS",
    "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "BAJAJHLDNG.NS",
    "BANDHANBNK.NS",
    "BANKBARODA.NS",
    "BANKINDIA.NS",
    "BDL.NS",
    "BEL.NS",
    "BHARATFORG.NS",
    "BHEL.NS",
    "BPCL.NS",
    "BHARTIARTL.NS",
    "BIOCON.NS",
    "BLUESTARCO.NS",
    "BOSCHLTD.NS",
    "BRITANNIA.NS",
    "CGPOWER.NS",
    "CANBK.NS",
    "CDSL.NS",
    "CHOLAFIN.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "COCHINSHIP.NS",
    "COFORGE.NS",
    "COLPAL.NS",
    "CAMS.NS",
    "CONCOR.NS",
    "CROMPTON.NS",
    "CUMMINSIND.NS",
    "DLF.NS",
    "DABUR.NS",
    "DALBHARAT.NS",
    "DELHIVERY.NS",
    "DIVISLAB.NS",
    "DIXON.NS",
    "DRREDDY.NS",
    "ETERNAL.NS",
    "EICHERMOT.NS",
    "EXIDEIND.NS",
    "FORCEMOT.NS",
    "NYKAA.NS",
    "FORTIS.NS",
    "GAIL.NS",
    "GMRAIRPORT.NS",
    "GLENMARK.NS",
    "GODFRYPHLP.NS",
    "GODREJCP.NS",
    "GODREJPROP.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCAMC.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HAVELLS.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HAL.NS",
    "HINDPETRO.NS",
    "HINDUNILVR.NS",
    "HINDZINC.NS",
    "POWERINDIA.NS",
    "HUDCO.NS",
    "HYUNDAI.NS",
    "ICICIBANK.NS",
    "ICICIGI.NS",
    "ICICIPRULI.NS",
    "IDFCFIRSTB.NS",
    "ITC.NS",
    "INDIANB.NS",
    "IEX.NS",
    "IOC.NS",
    "IRFC.NS",
    "IREDA.NS",
    "INDUSTOWER.NS",
    "INDUSINDBK.NS",
    "NAUKRI.NS",
    "INFY.NS",
    "INOXWIND.NS",
    "INDIGO.NS",
    "JINDALSTEL.NS",
    "JSWENERGY.NS",
    "JSWSTEEL.NS",
    "JIOFIN.NS",
    "JUBLFOOD.NS",
    "KEI.NS",
    "KPITTECH.NS",
    "KALYANKJIL.NS",
    "KAYNES.NS",
    "KFINTECH.NS",
    "KOTAKBANK.NS",
    "LTF.NS",
    "LICHSGFIN.NS",
    "LTM.NS",
    "LT.NS",
    "LAURUSLABS.NS",
    "LICI.NS",
    "LODHA.NS",
    "LUPIN.NS",
    "M&M.NS",
    "MANAPPURAM.NS",
    "MANKIND.NS",
    "MARICO.NS",
    "MARUTI.NS",
    "MFSL.NS",
    "MAXHEALTH.NS",
    "MAZDOCK.NS",
    "MOTILALOFS.NS",
    "MPHASIS.NS",
    "MCX.NS",
    "MUTHOOTFIN.NS",
    "NBCC.NS",
    "NHPC.NS",
    "NMDC.NS",
    "NTPC.NS",
    "NATIONALUM.NS",
    "NESTLEIND.NS",
    "NAM-INDIA.NS",
    "NUVAMA.NS",
    "OBEROIRLTY.NS",
    "ONGC.NS",
    "OIL.NS",
    "PAYTM.NS",
    "OFSS.NS",
    "POLICYBZR.NS",
    "PGEL.NS",
    "PIIND.NS",
    "PNBHOUSING.NS",
    "PAGEIND.NS",
    "PATANJALI.NS",
    "PERSISTENT.NS",
    "PETRONET.NS",
    "PIDILITIND.NS",
    "PPLPHARMA.NS",
    "POLYCAB.NS",
    "PFC.NS",
    "POWERGRID.NS",
    "PREMIERENE.NS",
    "PRESTIGE.NS",
    "PNB.NS",
    "RBLBANK.NS",
    "RECLTD.NS",
    "RVNL.NS",
    "RELIANCE.NS",
    "SBICARD.NS", "SBILIFE.NS", "SHREECEM.NS", "SRF.NS", "SAMMAANCAP.NS", "MOTHERSON.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SOLARINDS.NS", "SONACOMS.NS", "SBIN.NS", "SAIL.NS", "SUNPHARMA.NS", "SUPREMEIND.NS", "SUZLON.NS", "SWIGGY.NS", "TATACONSUM.NS", "TVSMOTOR.NS", "TCS.NS", "TATAELXSI.NS", "TMPV.NS", "TATAPOWER.NS", "TATASTEEL.NS", "TATATECH.NS", "TECHM.NS", "FEDERALBNK.NS", "INDHOTEL.NS", "PHOENIXLTD.NS", "TITAN.NS", "TORNTPHARM.NS", "TORNTPOWER.NS", "TRENT.NS", "TIINDIA.NS", "UNOMINDA.NS", "UPL.NS", "ULTRACEMCO.NS", "UNIONBANK.NS", "UNITDSPR.NS", "VBL.NS", "VEDL.NS", "VMM.NS", "IDEA.NS", "VOLTAS.NS", "WAAREEENER.NS", "WIPRO.NS", "YESBANK.NS", "ZYDUSLIFE.NS"
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
