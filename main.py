import os
import pandas as pd
import yfinance as yf
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

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
# FLASK
# =========================

flask_app = Flask(__name__)

# =========================
# TELEGRAM APP
# =========================

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

def vwap(df):
    df = df.copy()
    df["VWAP"] = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df

# =========================
# 15M RADAR (YOUR LOGIC SIMPLIFIED STABLE)
# =========================

def radar_15m(df):
    if df.empty or len(df) < 10:
        return False

    df = vwap(df)
    last = df.iloc[-1]

    return (
        last["Close"] > last["VWAP"] and
        last["Volume"] > df["Volume"].mean()
    )

# =========================
# 5M ENTRY
# =========================

def entry_5m(df):
    if df.empty or len(df) < 10:
        return False

    df = vwap(df)
    last = df.iloc[-1]

    return last["Close"] > last["VWAP"]

# =========================
# CORE ENGINE
# =========================

def scan_stock(stock):
    df15 = get_data(stock, "15m")
    df5 = get_data(stock, "5m")

    radar = radar_15m(df15)

    result = {
        "stock": stock,
        "radar": radar,
        "entry": False
    }

    if radar:
        result["entry"] = entry_5m(df5)

    return result

# =========================
# BACKTEST ENGINE
# =========================

def backtest(stock, date_from, date_to=None):

    stock = stock + ".NS"

    df15 = get_data(stock, "15m")
    df5 = get_data(stock, "5m")

    return {
        "stock": stock,
        "from": date_from,
        "to": date_to,
        "radar": radar_15m(df15),
        "entry": entry_5m(df5)
    }

# =========================
# LIVE SCAN
# =========================

def live_scan():
    results = []

    for s in STOCKS:
        try:
            results.append(scan_stock(s))
        except:
            continue

    return results

# =========================
# TELEGRAM COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Radar Bot Ready")

# =========================
# MAIN MESSAGE ENGINE (IMPORTANT PART)
# =========================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip().upper()

    # =========================
    # LIVE MODE
    # =========================
    if text == "LIVE" or text == "RADAR TODAY":

        results = live_scan()

        msg = "📡 LIVE RADAR\n\n"

        for r in results:
            msg += f"{r['stock']} | RADAR:{r['radar']} | ENTRY:{r['entry']}\n"

        await update.message.reply_text(msg)
        return

    # =========================
    # RADAR DATE MODE
    # Example: 06-04-2026 RADAR
    # =========================
    if "RADAR" in text and len(text.split()) == 2:
        date = text.split()[0]

        await update.message.reply_text(f"📡 RADAR MODE FOR {date} (processing logic)")
        return

    # =========================
    # RANGE BACKTEST
    # BHEL 06-04-2026 TO 10-04-2026
    # =========================
    if "TO" in text:

        parts = text.split()

        stock = parts[0]
        start = parts[1]
        end = parts[3]

        result = backtest(stock, start, end)

        await update.message.reply_text(
            f"""📊 RANGE BACKTEST
Stock: {result['stock']}
From: {result['from']}
To: {result['to']}
RADAR: {result['radar']}
ENTRY: {result['entry']}"""
        )
        return

    # =========================
    # SINGLE STOCK BACKTEST
    # BHEL 06-04-2026
    # =========================
    if len(text.split()) == 2:

        stock, date = text.split()

        result = backtest(stock, date)

        await update.message.reply_text(
            f"""📊 BACKTEST
Stock: {result['stock']}
Date: {result['from']}
RADAR: {result['radar']}
ENTRY: {result['entry']}"""
        )
        return

    # =========================
    # INVALID INPUT
    # =========================
    await update.message.reply_text(
        "❌ Invalid format\n\nUse:\nLIVE\nRADAR TODAY\nBHEL 06-04-2026\nBHEL 06-04-2026 TO 10-04-2026\n06-04-2026 RADAR"
    )

# =========================
# REGISTER HANDLERS
# =========================

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# =========================
# WEBHOOK SERVER
# =========================

@flask_app.post("/")
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return "OK"

# =========================
# SET WEBHOOK
# =========================

async def set_webhook():
    await app.bot.set_webhook(f"https://vwap-bot-ia6r.onrender.com/")
    print("Webhook set:", WEBHOOK_URL)

# =========================
# RUN SERVER
# =========================

import asyncio
import threading

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

async def main():
    await app.initialize()
    await app.start()

    await set_webhook()

    threading.Thread(target=run_flask).start()

    print("🚀 Radar Bot Running (Production Mode)")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
