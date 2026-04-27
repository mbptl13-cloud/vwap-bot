import os
import asyncio
from datetime import datetime, timedelta
from threading import Thread

import pandas as pd
import yfinance as yf
from flask import Flask

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================================================
# BOT TOKEN
# =====================================================

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")


# =====================================================
# FLASK KEEP ALIVE (RENDER)
# =====================================================

app_web = Flask(__name__)


@app_web.route("/")
def home():
    return "VWAP Bot Running"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_web)
    t.start()


# =====================================================
# HELPERS
# =====================================================


def safe_float(value):
    try:
        return float(value)
    except:
        return None


WATCHLIST = [
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


# =====================================================
# VWAP
# =====================================================


def calculate_vwap(df):
    df = df.copy()
    df["cum_vol"] = df["Volume"].cumsum()
    df["cum_vp"] = (df["Close"] * df["Volume"]).cumsum()
    df["VWAP"] = df["cum_vp"] / df["cum_vol"]
    return df


# =====================================================
# MAIN STRATEGY
# =====================================================


def find_trade(stock, date):
    try:
        start = date
        end = pd.to_datetime(date) + timedelta(days=1)

        df15 = yf.download(
            stock,
            interval="15m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True,
        )

        df5 = yf.download(
            stock,
            interval="5m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True,
        )

        if len(df15) < 10 or len(df5) < 20:
            return None

        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert("Asia/Kolkata").tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert("Asia/Kolkata").tz_localize(None)

        df15 = calculate_vwap(df15)
        df5 = calculate_vwap(df5)

        # 15M FILTER (your screenshot logic)
        df15["vol_sma_20"] = df15["Volume"].rolling(20).mean()
        valid_15m = []

        for idx, row in df15.iterrows():
            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            o = safe_float(row["Open"])
            h = safe_float(row["High"])
            l = safe_float(row["Low"])
            c = safe_float(row["Close"])
            v = safe_float(row["Volume"])
            vwap15 = safe_float(row["VWAP"])
            vol_sma = safe_float(row["vol_sma_20"])

            if None in [o, h, l, c, v, vwap15]:
                continue

            candle_range = h - l
            if candle_range <= 0:
                continue

            body = abs(c - o)

            cond1 = v > 500000
            cond2 = (c * v) > 150000000
            cond3 = ((candle_range / o) * 100) > 1
            cond4 = ((body / o) * 100) > 0.6
            cond5 = c > vwap15
            cond6 = vol_sma is not None and v > (2 * vol_sma)
            cond7 = c > o

            if cond1 and cond2 and cond3 and cond4 and cond5 and cond6 and cond7:
                valid_15m.append(idx)

        if not valid_15m:
            return None

        trigger_times = ", ".join([x.strftime("%H:%M") for x in valid_15m])

        return {
            "stock": stock,
            "valid_15m_count": len(valid_15m),
            "trigger_times": trigger_times,
        }

    except Exception as e:
        print(f"ERROR in {stock}: {str(e)}")
        return None


def full_date_scan(date):
    results = []
    for stock in WATCHLIST:
        result = find_trade(stock, date)
        if result:
            results.append(result)
    return results


# =====================================================
# TELEGRAM
# =====================================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if text == "LIVE":
        today = datetime.now().strftime("%Y-%m-%d")
        await update.message.reply_text(f"Scanning LIVE for {today}...")
        results = full_date_scan(today)
    elif len(text.split()) == 2 and text.split()[1] == "15M":
        scan_date = text.split()[0]
        await update.message.reply_text(f"Scanning 15M setups for {scan_date}...")
        results = full_date_scan(scan_date)
    elif len(text) == 10 and text.count("-") == 2:
        await update.message.reply_text(f"Scanning full F&O for {text}...")
        results = full_date_scan(text)
    else:
        await update.message.reply_text(
            "Use:\nLIVE\n2026-04-06\n2026-04-06 15M\nVEDL 2026-04-27"
        )
        return

    if not results:
        await update.message.reply_text("❌ No setups found")
        return

    msg = "🔥 RESULT\n\n"
    for r in results:
        msg += (
            f"{r['stock']}\n"
            f"15M Count: {r['valid_15m_count']}\n"
            f"15M Trigger: {r['trigger_times']}\n\n"
        )

    await update.message.reply_text(msg)


# =====================================================
# START
# =====================================================


async def main():
    print("BOT RUNNING...")
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    print("BOT STARTED")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
    
