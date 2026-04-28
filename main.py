import os
import asyncio
import threading
import pandas as pd
import yfinance as yf
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com")
PORT = int(os.getenv("PORT", 10000))

DEFAULT_STOCKS = [
    
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
    "SBICARD.NS",
    "SBILIFE.NS",
    "SHREECEM.NS",
    "SRF.NS",
    "SAMMAANCAP.NS",
    "MOTHERSON.NS",
    "SHRIRAMFIN.NS",
    "SIEMENS.NS",
    "SOLARINDS.NS",
    "SONACOMS.NS",
    "SBIN.NS",
    "SAIL.NS",
    "SUNPHARMA.NS",
    "SUPREMEIND.NS",
    "SUZLON.NS",
    "SWIGGY.NS",
    "TATACONSUM.NS",
    "TVSMOTOR.NS",
    "TCS.NS",
    "TATAELXSI.NS",
    "TMPV.NS",
    "TATAPOWER.NS",
    "TATASTEEL.NS",
    "TATATECH.NS",
    "TECHM.NS",
    "FEDERALBNK.NS",
    "INDHOTEL.NS",
    "PHOENIXLTD.NS",
    "TITAN.NS",
    "TORNTPHARM.NS",
    "TORNTPOWER.NS",
    "TRENT.NS",
    "TIINDIA.NS",
    "UNOMINDA.NS",
    "UPL.NS",
    "ULTRACEMCO.NS",
    "UNIONBANK.NS",
    "UNITDSPR.NS",
    "VBL.NS",
    "VEDL.NS",
    "VMM.NS",
    "IDEA.NS",
    "VOLTAS.NS",
    "WAAREEENER.NS",
    "WIPRO.NS",
    "YESBANK.NS",
    "ZYDUSLIFE.NS"
]


# =========================
# FLASK APP (WEBHOOK SERVER)
# =========================

flask_app = Flask(__name__)

# =========================
# TELEGRAM APP
# =========================

tg_app = Application.builder().token(BOT_TOKEN).build()

# =========================
# DATA
# =========================

def get_data(stock, interval, period="5d"):
    try:
        df = yf.download(stock, interval=interval, period=period, progress=False)
        df.dropna(inplace=True)
        return df
    except:
        return pd.DataFrame()

def add_vwap(df):
    df = df.copy()
    df["VWAP"] = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df

# =========================
# 15M RADAR (YOUR FULL LOGIC)
# =========================

def radar_15m(df15):
    if df15.empty or len(df15) < 20:
        return False, None

    df15 = add_vwap(df15)
    df15["vol_sma_20"] = df15["Volume"].rolling(20).mean()

    valid = []

    for idx, row in df15.iterrows():

        try:
            o = float(row["Open"])
            h = float(row["High"])
            l = float(row["Low"])
            c = float(row["Close"])
            v = float(row["Volume"])
            vwap = float(row["VWAP"])
            vol_sma = row["vol_sma_20"]
        except:
            continue

        if idx.time() <= pd.to_datetime("09:30").time():
            continue

        if any(pd.isna(x) for x in [o, h, l, c, v, vwap]):
            continue

        candle_range = h - l
        if candle_range <= 0:
            continue

        body = abs(c - o)

        # ===== YOUR CONDITIONS =====
        cond1 = v > 500000
        cond2 = (c * v) > 150000000
        cond3 = (candle_range / o) * 100 > 1
        cond4 = (body / o) * 100 > 0.6
        cond5 = c > vwap
        cond6 = vol_sma is not None and v > (2 * vol_sma)
        cond7 = c > o

        if cond1 and cond2 and cond3 and cond4 and cond5 and cond6 and cond7:
            valid.append(idx)

    if not valid:
        return False, None

    return True, valid[-1]

# =========================
# 5M ENTRY (VWAP BREAKOUT)
# =========================

def entry_5m(df5):
    if df5.empty or len(df5) < 20:
        return False, None, None

    df5 = add_vwap(df5)

    for i in range(1, len(df5)):

        prev = df5.iloc[i - 1]
        curr = df5.iloc[i]

        try:
            if (
                curr["Close"] > curr["VWAP"] and
                prev["Close"] < prev["VWAP"] and
                curr["Close"] > curr["Open"]
            ):
                return True, df5.index[i], float(curr["Close"])
        except:
            continue

    return False, None, None

# =========================
# CORE ENGINE
# =========================

def find_trade(stock):

    df15 = get_data(stock, "15m")
    df5 = get_data(stock, "5m")

    result = {
        "stock": stock,
        "radar": "NO",
        "entry": "NO",
        "time_15m": None,
        "time_5m": None,
        "price": None
    }

    radar, t15 = radar_15m(df15)

    if not radar:
        return result

    result["radar"] = "YES"
    result["time_15m"] = str(t15)

    entry, t5, price = entry_5m(df5)

    if entry:
        result["entry"] = "YES"
        result["time_5m"] = str(t5)
        result["price"] = round(price, 2)

    return result

# =========================
# SCANNER
# =========================

def scan_market():
    results = []

    for stock in DEFAULT_STOCKS:
        try:
            results.append(find_trade(stock))
        except Exception as e:
            print("Error:", stock, e)

    return results

# =========================
# TELEGRAM COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Hybrid Radar Bot Live (Webhook Mode)")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning Market...")

    results = scan_market()

    for r in results:
        await update.message.reply_text(
            f"""📡 {r['stock']}
RADAR: {r['radar']}
15M: {r['time_15m']}
ENTRY: {r['entry']}
PRICE: {r['price']}"""
        )

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("live", live))

# =========================
# WEBHOOK ENDPOINT
# =========================

@flask_app.post("/")
async def webhook():
    data = request.get_json(force=True)

    update = Update.de_json(data, tg_app.bot)

    await tg_app.process_update(update)

    return "OK"

# =========================
# SET WEBHOOK
# =========================

async def set_webhook():
    await tg_app.bot.set_webhook(f"{WEBHOOK_URL}/")
    print("Webhook set:", WEBHOOK_URL)

# =========================
# RUN FLASK SERVER
# =========================

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

# =========================
# MAIN (PRODUCTION SAFE)
# =========================

async def main():

    await tg_app.initialize()
    await tg_app.start()

    await set_webhook()

    thread = threading.Thread(target=run_flask)
    thread.start()

    print("🚀 Bot Running Successfully (Production Webhook Mode)")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
