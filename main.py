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

def get_data(stock, interval, start, end):
    try:
        df = yf.download(
            stock,
            interval=interval,
            start=start,
            end=end,
            progress=False,
            auto_adjust=True
        )

        df.dropna(inplace=True)
        return df

    except Exception as e:
        print("DATA ERROR:", stock, e)
        return pd.DataFrame()


# =====================================
# 15M RADAR CONDITION
# CHECK TIME = 09:45 TO 13:30
# =====================================

def radar_15m(df):
    print("15M CHECK RUNNING")
    if df.empty or len(df) < 20:
        return False, None

    df = add_vwap(df)

    df["vol_sma_20"] = (
        df["Volume"].rolling(20).mean()
    )

    valid_15m = []

    for idx, row in df.iterrows():

        current_time = idx.time()

        # =====================================
        # ONLY CHECK BETWEEN 09:45 → 13:30
        # =====================================

        if current_time < pd.to_datetime("09:45").time():
            continue

        if current_time > pd.to_datetime("13:30").time():
            continue

        try:
            o = float(row["Open"])
            h = float(row["High"])
            l = float(row["Low"])
            c = float(row["Close"])
            v = float(row["Volume"])
            vwap_15m = float(row["VWAP"])
            vol_sma = row["vol_sma_20"]

        except:
            continue

        candle_range = h - l

        if candle_range <= 0:
            continue

        body = abs(c - o)

        # =====================================
        # 15M CONDITIONS
        # =====================================

        # Condition 1 → High Volume
        cond1 = v > 500000

        # Condition 2 → Value Traded
        cond2 = (c * v) > 150000000

        # Condition 3 → Candle Range > 1%
        range_pct = (candle_range / o) * 100
        cond3 = range_pct > 1

        # Condition 4 → Candle Body > 0.6%
        body_pct = (body / o) * 100
        cond4 = body_pct > 0.6

        # Condition 5 → Close Above VWAP
        cond5 = c > vwap_15m

        # Condition 6 → Volume Spike
        cond6 = (
            pd.notna(vol_sma)
            and v > (2 * vol_sma)
        )

        # Condition 7 → Bullish Candle
        cond7 = c > o

        # =====================================
        # DEBUG PRINT
        # =====================================

        print(
            f"{idx} | "
            f"C1:{cond1} "
            f"C2:{cond2} "
            f"C3:{cond3} "
            f"C4:{cond4} "
            f"C5:{cond5} "
            f"C6:{cond6} "
            f"C7:{cond7}"
        )

        # =====================================
        # FINAL FILTER
        # =====================================

        if (
            cond1 and cond2 and cond3
            and cond4 and cond5
            and cond6 and cond7
        ):
            valid_15m.append(idx)

    if not valid_15m:
        return False, None

    # FIRST VALID CANDLE
    return True, valid_15m[0]


# =====================================
# 5M VWAP PRICE ACTION ENTRY
# CHECK AFTER 15M RADAR TRIGGER
# =====================================

def entry_5m(df, trigger_15m_time):
    if df.empty or len(df) < 10:
        return False, None, None

    df = add_vwap(df)

    valid_5m = []

    for idx, row in df.iterrows():

        current_time = idx.time()

        # =====================================
        # ONLY CHECK AFTER 15M TRIGGER
        # =====================================

        if idx <= trigger_15m_time:
            continue

        try:
            o = float(row["Open"])
            h = float(row["High"])
            l = float(row["Low"])
            c = float(row["Close"])
            vwap_5m = float(row["VWAP"])

        except:
            continue

        candle_range = h - l

        if candle_range <= 0:
            continue

        body = abs(c - o)

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # =====================================
        # 5M VWAP PRICE ACTION CONDITIONS
        # =====================================

        # Condition 1 → Price Above VWAP
        cond1 = c > vwap_5m

        # Condition 2 → Bullish Candle
        cond2 = c > o

        # Condition 3 → Strong Body
        body_pct = (body / o) * 100
        cond3 = body_pct > 0.25

        # Condition 4 → Rejection from VWAP
        cond4 = l <= vwap_5m and c > vwap_5m

        # Condition 5 → Small Upper Wick
        cond5 = upper_wick < body

        # =====================================
        # DEBUG PRINT
        # =====================================

        print(
            f"5M {idx} | "
            f"C1:{cond1} "
            f"C2:{cond2} "
            f"C3:{cond3} "
            f"C4:{cond4} "
            f"C5:{cond5}"
        )

        # =====================================
        # FINAL ENTRY FILTER
        # =====================================

        if (
            cond1 and cond2 and cond3
            and cond4 and cond5
        ):
            valid_5m.append((idx, c))

    if not valid_5m:
        return False, None, None

    # FIRST VALID ENTRY
    entry_time = valid_5m[0][0]
    entry_price = valid_5m[0][1]

    return True, entry_time, round(entry_price, 2)

# =========================
# CORE SCAN
# =========================

def scan_stock(stock, date=None):
    try:
        if date:
            start = pd.to_datetime(date).strftime("%Y-%m-%d")
            end = (
                pd.to_datetime(date) + pd.Timedelta(days=1)
            ).strftime("%Y-%m-%d")
        else:
            start = None
            end = None

        df15 = get_data(stock, "15m", start, end)
        df5 = get_data(stock, "5m", start, end)

        if df15.empty or df5.empty:
            return {
                "stock": stock,
                "radar": False,
                "entry": False,
                "t15": None,
                "t5": None,
                "price": None
            }

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

    except Exception as e:
        print("SCAN ERROR:", stock, e)

        return {
            "stock": stock,
            "radar": False,
            "entry": False,
            "t15": None,
            "t5": None,
            "price": None
        }

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

    # LIVE MODE
    if text in ["LIVE", "RADAR TODAY"]:
        return {"type": "live"}

    # DATE ONLY BACKTEST
    # Example: 2026-04-06
    if len(text.split()) == 1 and "-" in text:
        return {
            "type": "date_only",
            "date": text
        }

    # RADAR MODE
    # Example: 2026-04-06 RADAR
    if "RADAR" in text and len(text.split()) == 2:
        return {
            "type": "radar_date",
            "date": text.split()[0]
        }

    # RANGE BACKTEST
    # Example: BHEL 2026-04-01 TO 2026-04-20
    if "TO" in text:
        parts = text.split()
        return {
            "type": "range",
            "stock": parts[0],
            "start": parts[1],
            "end": parts[3]
        }

    # SINGLE STOCK BACKTEST
    # Example: BHEL 2026-04-06
    parts = text.split()
    if len(parts) == 2:
        return {
            "type": "single",
            "stock": parts[0],
            "date": parts[1]
        }

    return {"type": "invalid"}

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    print("INPUT:", text)

    req = parse_input(text)

    # =========================
    # LIVE MODE
    # =========================
    if req["type"] == "live":
        await update.message.reply_text("📡 LIVE SCAN STARTED...")
        await live(update, context)
        return

    # =========================
    # DATE ONLY BACKTEST
    # Example: 2026-04-06
    # =========================
    if req["type"] == "date_only":
        date = req["date"]

        await update.message.reply_text(
            f"📊 FULL MARKET BACKTEST STARTED...\nDate: {date}"
        )

        try:
            results = []

            for stock in STOCKS:
                result = scan_stock(stock, date)
                if result["radar"]:
                    results.append(result)

            if not results:
                await update.message.reply_text(
                    f"❌ No radar signals found for {date}"
                )
                return

            msg = f"📊 BACKTEST RESULT ({date})\n\n"

            for r in results[:15]:
                msg += (
                    f"{r['stock']} | "
                    f"RADAR:{r['radar']} | "
                    f"ENTRY:{r['entry']}\n"
                )

            await update.message.reply_text(msg)

        except Exception as e:
            await update.message.reply_text(
                f"❌ BACKTEST ERROR: {str(e)}"
            )
        return

    # =========================
    # RADAR DATE MODE
    # Example: 2026-04-06 RADAR
    # =========================
    if req["type"] == "radar_date":
        await update.message.reply_text(
            f"📡 RADAR MODE ACTIVE\nDate: {req['date']}"
        )
        return

    # =========================
    # RANGE BACKTEST
    # Example:
    # BHEL 2026-04-01 to 2026-04-20
    # =========================
    if req["type"] == "range":
        stock = req["stock"]
        start = req["start"]
        end = req["end"]

        await update.message.reply_text(
            f"📊 RANGE BACKTEST STARTED...\n{stock}\n{start} → {end}"
        )

        try:
            result = scan_stock(stock + ".NS", start)

            await update.message.reply_text(
                f"""📊 RANGE RESULT

Stock: {stock}
From: {start}
To: {end}

RADAR: {result['radar']}
ENTRY: {result['entry']}
15M TIME: {result['t15']}
5M TIME: {result['t5']}
PRICE: {result['price']}"""
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ RANGE ERROR: {str(e)}"
            )
        return

    # =========================
    # SINGLE STOCK BACKTEST
    # Example:
    # ADANIGREEN 2026-04-06
    # =========================
    if req["type"] == "single":
        stock = req["stock"]
        date = req["date"]

        await update.message.reply_text(
            f"📊 BACKTEST STARTED...\nStock: {stock}\nDate: {date}"
        )

        try:
            result = scan_stock(stock + ".NS", date)

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

        except Exception as e:
            await update.message.reply_text(
                f"❌ SINGLE BACKTEST ERROR: {str(e)}"
            )
        return

    # =========================
    # INVALID INPUT
    # =========================
    await update.message.reply_text(
        "❌ INVALID INPUT FORMAT"
    )

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
