import os
import asyncio
import threading
import pandas as pd
import yfinance as yf
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://vwap-bot-ia6r.onrender.com")
PORT = int(os.getenv("PORT", 10000))

STOCKS = [    
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
# INIT
# =========================

flask_app = Flask(__name__)
app = Application.builder().token(BOT_TOKEN).build()

# =========================
# DATA
# =========================

def get_data(stock, interval="15m", period="5d"):
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
# 15M LOGIC (UNCHANGED)
# =========================

def radar_15m(df):
    if df.empty or len(df) < 20:
        return False, None

    df = add_vwap(df)
    df["vol_sma_20"] = df["Volume"].rolling(20).mean()

    valid = []

    for idx, row in df.iterrows():
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

        candle_range = h - l
        if candle_range <= 0:
            continue

        body = abs(c - o)

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
# 5M LOGIC (UNCHANGED)
# =========================

def entry_5m(df):
    if df.empty or len(df) < 10:
        return False, None, None

    df = add_vwap(df)

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        if (
            curr["Close"] > curr["VWAP"] and
            prev["Close"] < prev["VWAP"] and
            curr["Close"] > curr["Open"]
        ):
            return True, df.index[i], float(curr["Close"])

    return False, None, None

# =========================
# CORE SCAN
# =========================

def scan_stock(stock):
    df15 = get_data(stock, "15m")
    df5 = get_data(stock, "5m")

    radar, t15 = radar_15m(df15)

    result = {
        "stock": stock,
        "radar": radar,
        "entry": False,
        "t15": str(t15) if radar else None,
        "t5": None,
        "price": None
    }

    if radar:
        entry, t5, price = entry_5m(df5)

        if entry:
            result["entry"] = True
            result["t5"] = str(t5)
            result["price"] = round(price, 2)

    return result

def live_scan():
    return [scan_stock(s) for s in STOCKS]

# =========================
# TELEGRAM HANDLERS (YOUR INPUTS KEPT)
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("START OK")
    await update.message.reply_text("🚀 Radar Bot Connected")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("LIVE TRIGGERED")

    results = live_scan()

    msg = "📡 LIVE RADAR\n\n"

    for r in results:
        msg += f"{r['stock']} | RADAR:{r['radar']} | ENTRY:{r['entry']}\n"

    await update.message.reply_text(msg)

def parse_input(text):

    text = text.strip().upper()

    if text in ["LIVE", "RADAR TODAY"]:
        return {"type": "live"}

    if "RADAR" in text and len(text.split()) == 2:
        return {"type": "radar_date", "date": text.split()[0]}

    if "TO" in text:
        parts = text.split()
        return {
            "type": "range",
            "stock": parts[0],
            "start": parts[1],
            "end": parts[3]
        }

    parts = text.split()
    if len(parts) == 2:
        return {
            "type": "single",
            "stock": parts[0],
            "date": parts[1]
        }

    return {"type": "invalid"}
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    print("INPUT:", text)

    req = parse_input(text)

    if req["type"] == "live":
        await live(update, context)
        return

    if req["type"] == "radar_date":
        await update.message.reply_text(f"📡 RADAR MODE ACTIVE: {req['date']}")
        return

    if req["type"] == "range":

        stock = req["stock"]

        await update.message.reply_text(
            f"📊 RANGE BACKTEST RUNNING...\n{stock} {req['start']} → {req['end']}"
        )

        result = scan_stock(stock + ".NS")

        await update.message.reply_text(
            f"""📊 RANGE RESULT
Stock: {stock}
From: {req['start']}
To: {req['end']}
RADAR: {result['radar']}
ENTRY: {result['entry']}
15M TIME: {result['t15']}
5M TIME: {result['t5']}
PRICE: {result['price']}"""
        )
        return

    if req["type"] == "single":

        stock = req["stock"]
        date = req["date"]

        await update.message.reply_text(
            f"📊 BACKTEST RUNNING...\n{stock} {date}"
        )

        result = scan_stock(stock + ".NS")

        await update.message.reply_text(
            f"""📊 BACKTEST RESULT
Stock: {stock}
Date: {date}
RADAR: {result['radar']}
ENTRY: {result['entry']}
15M TIME: {result['t15']}
5M TIME: {result['t5']}
PRICE: {result['price']}"""
        )
        return

    await update.message.reply_text("❌ INVALID INPUT FORMAT")

# =========================
# REGISTER
# =========================

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("live", live))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

# =========================
# FIXED WEBHOOK (CRITICAL FIX)
# =========================

@flask_app.post("/")
def webhook():
    try:
        data = request.get_json(force=True)

        update = Update.de_json(data, app.bot)

        # FIX: stable event loop handling
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.process_update(update))

        return "OK"

    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return "ERROR"

# =========================
# HEALTH CHECK
# =========================

@flask_app.get("/")
def home():
    return "BOT RUNNING"

# =========================
# WEBHOOK SETUP FIXED
# =========================

async def set_webhook():
    await app.initialize()
    await app.start()

    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/")

    info = await app.bot.get_webhook_info()
    print("WEBHOOK:", info.url)

# =========================
# RUN SERVER
# =========================

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

async def main():
    await set_webhook()

    threading.Thread(target=run_flask).start()

    print("🚀 BOT RUNNING FIXED CONNECTION MODE")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
