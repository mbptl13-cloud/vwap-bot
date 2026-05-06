import yfinance as yf
import pandas as pd
import numpy as np
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

BATCH_WORKERS = 6
STOCK_WORKERS = 5

bot = Bot(token=TOKEN)
app = Flask(__name__)

last_run_key = None

# ================= YOUR STOCK LIST =================
FNO_STOCKS = FNO_STOCKS = [
"360ONE.NS","ABB.NS","APLAPOLLO.NS","AUBANK.NS","ADANIENSOL.NS","ADANIENT.NS","ADANIGREEN.NS","ADANIPORTS.NS","ADANIPOWER.NS","ABCAPITAL.NS","ALKEM.NS","AMBER.NS","AMBUJACEM.NS","ANGELONE.NS","APOLLOHOSP.NS","ASHOKLEY.NS","ASIANPAINT.NS","ASTRAL.NS","AUROPHARMA.NS","DMART.NS",

"AXISBANK.NS","BSE.NS","BAJAJ-AUTO.NS","BAJFINANCE.NS","BAJAJFINSV.NS","BAJAJHLDNG.NS","BANDHANBNK.NS","BANKBARODA.NS","BANKINDIA.NS","BDL.NS","BEL.NS","BHARATFORG.NS","BHEL.NS","BPCL.NS","BHARTIARTL.NS","BIOCON.NS","BLUESTARCO.NS","BOSCHLTD.NS","BRITANNIA.NS","CGPOWER.NS",

"CANBK.NS","CDSL.NS","CHOLAFIN.NS","CIPLA.NS","COALINDIA.NS","COCHINSHIP.NS","COFORGE.NS","COLPAL.NS","CAMS.NS","CONCOR.NS","CROMPTON.NS","CUMMINSIND.NS","DLF.NS","DABUR.NS","DALBHARAT.NS","DELHIVERY.NS","DIVISLAB.NS","DIXON.NS","DRREDDY.NS","ETERNAL.NS",

"EICHERMOT.NS","EXIDEIND.NS","FORCEMOT.NS","NYKAA.NS","FORTIS.NS","GAIL.NS","GMRAIRPORT.NS","GLENMARK.NS","GODFRYPHLP.NS","GODREJCP.NS","GODREJPROP.NS","GRASIM.NS","HCLTECH.NS","HDFCAMC.NS","HDFCBANK.NS","HDFCLIFE.NS","HAVELLS.NS","HEROMOTOCO.NS","HINDALCO.NS","HAL.NS",

"HINDPETRO.NS","HINDUNILVR.NS","HINDZINC.NS","POWERINDIA.NS","HUDCO.NS","HYUNDAI.NS","ICICIBANK.NS","ICICIGI.NS","ICICIPRULI.NS","IDFCFIRSTB.NS","ITC.NS","INDIANB.NS","IEX.NS","IOC.NS","IRFC.NS","IREDA.NS","INDUSTOWER.NS","INDUSINDBK.NS","NAUKRI.NS","INFY.NS",

"INOXWIND.NS","INDIGO.NS","JINDALSTEL.NS","JSWENERGY.NS","JSWSTEEL.NS","JIOFIN.NS","JUBLFOOD.NS","KEI.NS","KPITTECH.NS","KALYANKJIL.NS","KAYNES.NS","KFINTECH.NS","KOTAKBANK.NS","LTF.NS","LICHSGFIN.NS","LTM.NS","LT.NS","LAURUSLABS.NS","LICI.NS","LODHA.NS",

"LUPIN.NS","M&M.NS","MANAPPURAM.NS","MANKIND.NS","MARICO.NS","MARUTI.NS","MFSL.NS","MAXHEALTH.NS","MAZDOCK.NS","MOTILALOFS.NS","MPHASIS.NS","MCX.NS","MUTHOOTFIN.NS","NBCC.NS","NHPC.NS","NMDC.NS","NTPC.NS","NATIONALUM.NS","NESTLEIND.NS","NAM-INDIA.NS",

"NUVAMA.NS","OBEROIRLTY.NS","ONGC.NS","OIL.NS","PAYTM.NS","OFSS.NS","POLICYBZR.NS","PGEL.NS","PIIND.NS","PNBHOUSING.NS","PAGEIND.NS","PATANJALI.NS","PERSISTENT.NS","PETRONET.NS","PIDILITIND.NS","PPLPHARMA.NS","POLYCAB.NS","PFC.NS","POWERGRID.NS","PREMIERENE.NS",

"PRESTIGE.NS","PNB.NS","RBLBANK.NS","RECLTD.NS","RVNL.NS","RELIANCE.NS","SBICARD.NS","SBILIFE.NS","SHREECEM.NS","SRF.NS","SAMMAANCAP.NS","MOTHERSON.NS","SHRIRAMFIN.NS","SIEMENS.NS","SOLARINDS.NS","SONACOMS.NS","SBIN.NS","SAIL.NS","SUNPHARMA.NS","SUPREMEIND.NS",

"SUZLON.NS","SWIGGY.NS","TATACONSUM.NS","TVSMOTOR.NS","TCS.NS","TATAELXSI.NS","TMPV.NS","TATAPOWER.NS","TATASTEEL.NS","TATATECH.NS","TECHM.NS","FEDERALBNK.NS","INDHOTEL.NS","PHOENIXLTD.NS","TITAN.NS","TORNTPHARM.NS","TORNTPOWER.NS","TRENT.NS","TIINDIA.NS","UNOMINDA.NS",

"UPL.NS","ULTRACEMCO.NS","UNIONBANK.NS","UNITDSPR.NS","VBL.NS","VEDL.NS","VMM.NS","IDEA.NS","VOLTAS.NS","WAAREEENER.NS","WIPRO.NS","YESBANK.NS","ZYDUSLIFE.NS"
]

# ================= TELEGRAM =================
async def send_telegram(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print("📤", msg)
    except Exception as e:
        print("Telegram Error:", e)

# ================= STRATEGY =================
def check_conditions(df):
    try:
        df = df.copy()
        df["vwap"] = (
            (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum()
            / df["Volume"].cumsum()
        )
        df["vol_sma20"] = df["Volume"].rolling(20).mean()

        last = df.iloc[-1]

        return (
            last["Volume"] > 500000
            and (last["Close"] * last["Volume"]) > 150000000
            and ((last["High"] - last["Low"]) / last["Open"] * 100) > 1
            and (abs(last["Close"] - last["Open"]) / last["Open"] * 100) > 0.6
            and last["Close"] > last["vwap"]
            and last["Volume"] > (last["vol_sma20"] * 2)
            and last["Close"] > last["Open"]
        )
    except:
        return False

# ================= BATCH =================
def create_batches(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

# ================= PROCESS =================
def process_stock(stock):
    try:
        df = yf.download(stock, interval="15m", period="3d", progress=False)

        if len(df) < 30:
            return None

        if check_conditions(df):
            return stock.replace(".NS", "")

    except Exception as e:
        print(stock, e)

    return None

def process_batch(batch):
    results = []

    with ThreadPoolExecutor(max_workers=STOCK_WORKERS) as executor:
        futures = [executor.submit(process_stock, s) for s in batch]

        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    return results

# ================= SCAN =================
def scan_market():
    print("✅ SCAN EXECUTED")

    batches = create_batches(FNO_STOCKS, BATCH_WORKERS)
    all_results = []

    with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as executor:
        futures = [executor.submit(process_batch, batch) for batch in batches]

        for future in as_completed(futures):
            all_results.extend(future.result())

    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M")

    if all_results:
        msg = f"✅ SCAN EXECUTED\n📊 15M SCAN\n⏰ {now}\n\n🔥 STOCKS:\n" + "\n".join(all_results)
    else:
        msg = f"✅ SCAN EXECUTED\n📊 15M SCAN\n⏰ {now}\n\n❌ NO STOCK"

    asyncio.run(send_telegram(msg))

# ================= LOOP =================
def run_loop():
    global last_run_key

    print("🚀 Loop Started")

    ist = pytz.timezone("Asia/Kolkata")

    while True:
        now = datetime.datetime.now(ist)
        current_time = now.time()

        # market hours only: 09:15 to 15:30
        if datetime.time(9, 15) <= current_time <= datetime.time(15, 30):

            # exact scan times: 09:31, 09:46, 10:01...
            if now.minute % 15 == 1:
                key = now.strftime("%Y-%m-%d %H:%M")

                if key != last_run_key:
                    last_run_key = key
                    print(f"⏰ Trigger {key}")
                    scan_market()

        time.sleep(5)

# ================= FLASK =================
@app.route("/")
def home():
    return "Bot Running ✅"

# ================= MAIN =================
if __name__ == "__main__":
    print("🔥 Starting Bot")

    asyncio.run(send_telegram("🚀 BOT STARTED"))

    # immediate startup scan
    scan_market()

    t = threading.Thread(target=run_loop)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
