import os
import re
import asyncio
import pandas as pd
import yfinance as yf
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
WEBHOOK_URL = "https://vwap-bot-ia6r.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# =========================================================
# STOCK LIST (SHORT SAMPLE - ADD FULL IF NEEDED)
# =========================================================

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

# =========================================================
# DATA
# =========================================================

def download_data(symbol, interval="5m", period="5d"):
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False)
        if df is None or df.empty:
            return None
        df.dropna(inplace=True)
        return df
    except:
        return None


def filter_market_time(df):
    if df is None or df.empty:
        return None
    try:
        if getattr(df.index, "tz", None):
            df.index = df.index.tz_localize(None)
        df = df.between_time("09:45", "13:30")
        return df if not df.empty else None
    except:
        return None


def vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

# =========================================================
# 15M RADAR
# =========================================================

def check_15m(df):
    if df is None or len(df) < 20:
        return None

    df = df.copy()
    df["VWAP"] = vwap(df)
    df["SMA20"] = df["Volume"].rolling(20).mean()

    for i in range(20, len(df)):
        r = df.iloc[i]

        if (
            r["Volume"] > 500000 and
            r["Close"] * r["Volume"] > 150000000 and
            r["Close"] > r["VWAP"] and
            r["Volume"] > 2 * r["SMA20"] and
            r["Close"] > r["Open"]
        ):
            return {"time": df.index[i], "close": float(r["Close"])}

    return None

# =========================================================
# 5M TRADE
# =========================================================

def check_5m(df, radar_time):
    if df is None or df.empty:
        return None

    df = df[df.index > radar_time]
    if df.empty:
        return None

    df = df.copy()
    df["VWAP"] = vwap(df)

    for i in range(len(df)):
        r = df.iloc[i]

        if r["Low"] <= r["VWAP"] <= r["High"] and r["Close"] > r["Open"]:
            entry = r["High"]
            sl = r["Low"]
            risk = entry - sl

            if risk <= 0:
                continue

            target = entry + (risk * 2)

            return {
                "time": df.index[i],
                "entry": round(entry, 2),
                "sl": round(sl, 2),
                "target": round(target, 2)
            }

    return None

# =========================================================
# SCANNER
# =========================================================

def scan_stock(symbol):
    df15 = filter_market_time(download_data(symbol, "15m"))
    radar = check_15m(df15)

    if not radar:
        return None

    df5 = filter_market_time(download_data(symbol, "5m"))
    trade = check_5m(df5, radar["time"])

    return {"symbol": symbol, "radar": radar, "trade": trade}


def full_scan():
    results = []
    for s in FNO_STOCKS:
        r = scan_stock(s)
        if r:
            results.append(r)
    return results

# =========================================================
# FORMAT
# =========================================================

def format_result(r):
    msg = f"📊 {r['symbol']}\n15M: {r['radar']['time']}\n"

    if r.get("trade"):
        t = r["trade"]
        msg += f"5M: {t['time']}\nEntry: {t['entry']}\nSL: {t['sl']}\nTarget: {t['target']}"
    else:
        msg += "RADAR ACTIVE - Waiting 5M"

    return msg

# =========================================================
# TELEGRAM HANDLERS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Bot Ready\n\nCommands:\nLIVE\nRADAR TODAY\nBHEL 2026-04-06\n2026-04-06 RADAR\n2026-04-06"
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    await update.message.reply_text(f"⏳ Processing: {text}")

    # LIVE
    if text == "LIVE":
        res = full_scan()
        for r in res:
            await update.message.reply_text(format_result(r))
        return

    # RADAR TODAY
    if text == "RADAR TODAY":
        res = full_scan()
        await update.message.reply_text("\n".join([r["symbol"] for r in res]))
        return

    # STOCK + DATE
    if re.fullmatch(r"[A-Z]+\s\d{4}-\d{2}-\d{2}", text):
        stock = text.split()[0] + ".NS"
        r = scan_stock(stock)
        await update.message.reply_text(format_result(r) if r else "No setup")
        return

    # DATE RADAR
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\sRADAR", text):
        res = full_scan()
        await update.message.reply_text("\n".join([r["symbol"] for r in res]))
        return

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        res = full_scan()
        for r in res:
            await update.message.reply_text(format_result(r))
        return

    await update.message.reply_text("Invalid command")

# =========================================================
# TELEGRAM APP
# =========================================================

telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT, handle))

# =========================================================
# WEBHOOK
# =========================================================

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_app.process_update(update))

    return "ok"


@app.route("/")
def home():
    return "Bot Running"

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
