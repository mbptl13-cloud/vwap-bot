import os
import re
import asyncio
import pandas as pd
import yfinance as yf
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
WEBHOOK_URL = "https://vwap-bot-ia6r.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

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


def normalize_dataframe(df):
    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        return None

    df = df.copy()
    df = df[required_columns]
    df.dropna(inplace=True)

    if df.empty:
        return None

    return df


def download_data(symbol, interval="5m", period="5d"):
    try:
        df = yf.download(
            tickers=symbol,
            interval=interval,
            period=period,
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        return normalize_dataframe(df)

    except Exception as e:
        print(f"Download Error {symbol}: {e}")
        return None


def filter_market_time(df):
    if df is None or df.empty:
        return None

    df = df.copy()

    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_localize(None)

    try:
        df = df.between_time("09:45", "13:30")
    except Exception:
        return None

    if df.empty:
        return None

    return df


def calculate_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    volume_cumsum = df["Volume"].cumsum()

    if (volume_cumsum == 0).any():
        return None

    return (tp * df["Volume"]).cumsum() / volume_cumsum


def candle_body(row):
    return abs(float(row["Close"]) - float(row["Open"]))


def candle_range(row):
    return float(row["High"]) - float(row["Low"])


def check_15m_condition(df):
    if df is None or len(df) < 20:
        return None

    df = df.copy()
    vwap = calculate_vwap(df)

    if vwap is None:
        return None

    df["VWAP"] = vwap
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    for i in range(19, len(df)):
        row = df.iloc[i]

        if pd.isna(row["VOL_SMA20"]):
            continue

        open_price = float(row["Open"])
        if open_price <= 0:
            continue

        volume_ok = float(row["Volume"]) > 500000
        value_ok = (float(row["Volume"]) * float(row["Close"])) > 150000000

        range_pct = (candle_range(row) / open_price) * 100
        body_pct = (candle_body(row) / open_price) * 100

        range_ok = range_pct > 0.6
        body_ok = body_pct > 0.6
        vwap_ok = float(row["Close"]) > float(row["VWAP"])
        vol_surge_ok = float(row["Volume"]) > (2 * float(row["VOL_SMA20"]))
        bullish_ok = float(row["Close"]) > float(row["Open"])

        if all([
            volume_ok,
            value_ok,
            range_ok,
            body_ok,
            vwap_ok,
            vol_surge_ok,
            bullish_ok,
        ]):
            return {
                "time": df.index[i],
                "close": round(float(row["Close"]), 2),
            }

    return None


def check_5m_trade(df, radar_time):
    if df is None or df.empty:
        return None

    df = df.copy()
    df = df[df.index > radar_time]

    if df.empty:
        return None

    vwap = calculate_vwap(df)
    if vwap is None:
        return None

    df["VWAP"] = vwap

    for i in range(len(df)):
        row = df.iloc[i]

        low_price = float(row["Low"])
        high_price = float(row["High"])
        open_price = float(row["Open"])
        close_price = float(row["Close"])
        vwap_value = float(row["VWAP"])

        vwap_touch = low_price <= vwap_value <= high_price
        bullish_close = close_price > open_price

        if not (vwap_touch and bullish_close):
            continue

        entry = round(high_price, 2)
        sl = round(low_price, 2)
        risk = round(entry - sl, 2)

        if risk <= 0:
            continue

        if risk < round(entry * 0.003, 2):
            continue

        target = round(entry + (risk * 2), 2)

        return {
            "time": df.index[i],
            "entry": entry,
            "sl": sl,
            "target": target,
        }

    return None


def scan_stock(symbol):
    try:
        df15 = filter_market_time(download_data(symbol, "15m", "5d"))
        radar = check_15m_condition(df15)

        if not radar:
            return None

        df5 = filter_market_time(download_data(symbol, "5m", "5d"))
        trade = check_5m_trade(df5, radar["time"])

        return {
            "symbol": symbol,
            "radar": radar,
            "trade": trade,
        }

    except Exception as e:
        print(f"Scan Error {symbol}: {e}")
        return None


def full_scan():
    results = []

    for stock in FNO_STOCKS:
        result = scan_stock(stock)
        if result is not None:
            results.append(result)

    return results


def format_result(result):
    message = f"📊 {result['symbol']}\n"
    message += f"15M Time: {result['radar']['time']}\n"

    trade = result.get("trade")

    if trade:
        message += f"5M Time: {trade['time']}\n"
        message += f"Entry: {trade['entry']}\n"
        message += f"SL: {trade['sl']}\n"
        message += f"Target: {trade['target']}\n"
    else:
        message += "RADAR ACTIVE → Waiting for 5M Setup\n"

    return message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🤖 NSE F&O HYBRID BOT READY

Commands:

LIVE
RADAR TODAY
2026-04-06
BHEL 2026-04-06
BHEL 2026-04-06 to 2026-04-10
2026-04-06 RADAR
"""
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().upper()

    await update.message.reply_text(
        f"⏳ Processing: {text}\nPlease wait..."
    )

    if text == "LIVE":
        results = full_scan()

        if not results:
            await update.message.reply_text("No setups found.")
            return

        for result in results:
            await update.message.reply_text(format_result(result))
        return

    if text == "RADAR TODAY":
        results = full_scan()
        radar_lines = []

        for result in results:
            if result.get("radar"):
                radar_lines.append(
                    f"{result['symbol']} → {result['radar']['time']}"
                )

        if radar_lines:
            await update.message.reply_text("\n".join(radar_lines))
        else:
            await update.message.reply_text("No radar found today.")
        return

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}(\s+RADAR)?", text):
        await update.message.reply_text(
            f"Scanning full F&O for {text}"
        )

        results = full_scan()

        if results:
            for result in results:
                await update.message.reply_text(format_result(result))
        else:
            await update.message.reply_text("No setups found.")
        return

    await update.message.reply_text("Invalid command. Use /start")


telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
)


@app.route("/")
def home():
    return "Bot Running Successfully"


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, bot)

    if update is not None:
        asyncio.run(telegram_app.process_update(update))

    return "ok"


if __name__ == "__main__":
    print("🤖 HYBRID BOT RUNNING...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(telegram_app.initialize())
    loop.run_until_complete(telegram_app.start())

    app.run(
        host="0.0.0.0",
        port=PORT
        )
        
