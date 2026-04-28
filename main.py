import pandas as pd
import numpy as np
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =========================
# CONFIG
# =========================

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
BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

# =========================
# DATA FETCH
# =========================

def get_data(stock, interval, start, end):
    df = yf.download(stock, interval=interval, start=start, end=end, progress=False)
    df.dropna(inplace=True)
    return df

# =========================
# VWAP
# =========================

def add_vwap(df):
    df = df.copy()
    if df.empty:
        return df
    df["vwap"] = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df

# =========================
# 15M RADAR
# =========================

def radar_15m(df):
    if df.empty or len(df) < 20:
        return False, None

    df = add_vwap(df)

    last = df.iloc[-1]
    vol_avg = df["Volume"].rolling(10).mean().iloc[-1]

    condition = (
        last["Close"] > last["vwap"] and
        last["Volume"] > vol_avg
    )

    return condition, df.index[-1]

# =========================
# 5M ENTRY
# =========================

def entry_5m(df):
    if df.empty or len(df) < 20:
        return False, None, None

    df = add_vwap(df)
    last = df.iloc[-1]

    condition = last["Close"] > last["vwap"]

    return condition, df.index[-1], last["Close"]

# =========================
# CORE ENGINE
# =========================

def find_trade(stock, df_15m, df_5m):

    result = {
        "stock": stock,
        "radar_alert": "NO",
        "trigger_15m": None,
        "five_min_entry": "NO",
        "entry_time": None,
        "entry": None,
        "sl": None,
        "target": None,
        "score": "0/5",
        "result": "NO_TRADE"
    }

    radar, t15 = radar_15m(df_15m)

    if not radar:
        return result

    result["radar_alert"] = "YES"
    result["trigger_15m"] = str(t15)

    score = 3

    entry, t5, price = entry_5m(df_5m)

    if entry:
        result["five_min_entry"] = "YES"
        result["entry_time"] = str(t5)

        entry_price = price
        sl = entry_price * 0.988
        target = entry_price * 1.03

        result["entry"] = round(entry_price, 2)
        result["sl"] = round(sl, 2)
        result["target"] = round(target, 2)

        score += 2
        result["result"] = "TRADE"

    result["score"] = f"{score}/5"

    return result

# =========================
# SCANNER
# =========================

def scan(stocks, start, end):

    results = []

    for stock in stocks:
        try:
            df_15m = get_data(stock, "15m", start, end)
            df_5m = get_data(stock, "5m", start, end)

            if df_15m.empty or df_5m.empty:
                continue

            results.append(find_trade(stock, df_15m, df_5m))

        except Exception as e:
            print("Error:", stock, e)

    return results

# =========================
# MODES
# =========================

def live_scan(date="2026-04-06"):
    return scan(DEFAULT_STOCKS, date, date)


def backtest(date):
    return scan(DEFAULT_STOCKS, date, date)


def single_stock(stock, date):
    return scan([stock], date, date)


def range_backtest(stock, start, end):
    return scan([stock], start, end)

# =========================
# RADAR ONLY
# =========================

def radar_only(stock, date):

    df_15m = get_data(stock, "15m", date, date)
    df_5m = get_data(stock, "5m", date, date)

    radar, t15 = radar_15m(df_15m)

    if radar:
        entry, t5, price = entry_5m(df_5m)

        if entry:
            return {
                "stock": stock,
                "radar": "YES",
                "time_15m": str(t15),
                "time_5m": str(t5),
                "status": "TRADE CONFIRMED"
            }

        return {
            "stock": stock,
            "radar": "YES",
            "time_15m": str(t15),
            "status": "WAIT 5M"
        }

    return {"stock": stock, "radar": "NO"}

# =========================
# TELEGRAM BOT
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Hybrid Radar Bot Ready\nUse /live to scan")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning market...")

    signals = live_scan()

    if not signals:
        await update.message.reply_text("No signals ❌")
        return

    for s in signals:
        msg = f"""
📡 {s['stock']}
⚡ RADAR: {s['radar_alert']}
⏱ 15M: {s['trigger_15m']}
🎯 ENTRY: {s['five_min_entry']}
📊 SCORE: {s['score']}
💰 ENTRY: {s['entry']}
🛑 SL: {s['sl']}
🚀 TARGET: {s['target']}
"""
        await update.message.reply_text(msg)

# =========================
# RUN BOT
# =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))

    print("Bot running...")
    app.run_polling()

# =========================
# TEST MODE
# =========================

if __name__ == "__main__":
    main()
    
