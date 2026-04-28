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

def get_data(stock, interval, start=None, end=None):
    try:
        print(f"DOWNLOADING: {stock} | {interval}")

        df = yf.download(
            tickers=stock,
            interval=interval,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
            threads=False,
            prepost=False
        )

        if df is None or df.empty:
            print(f"NO DATA: {stock} | {interval}")
            return pd.DataFrame()

        df.dropna(inplace=True)

        print(f"DATA OK: {stock} | {interval} | Rows: {len(df)}")

        return df

    except Exception as e:
        print(f"DOWNLOAD ERROR: {stock} | {interval} | {e}")
        return pd.DataFrame()



# =========================================
# FINAL WORKING LOGIC
# 15M FIRST → THEN 5M ENTRY
# USING YOUR WORKING STRUCTURE
# =========================================

def find_trade(df15, df5, stock):
    try:
        if df15.empty or df5.empty:
            return {
                "stock": stock,
                "radar": False,
                "entry": False,
                "t15": None,
                "t5": None,
                "entry_price": None,
                "sl": None,
                "target": None,
                "result": "NO DATA"
            }

        # =========================
        # ADD VWAP
        # =========================

        df15 = add_vwap(df15)
        df5 = add_vwap(df5)

        # =========================
        # DAY HIGH
        # =========================

        day_high = df15["High"].max()

        # =========================
        # LOOP THROUGH 5M CANDLES
        # =========================

        for i in range(1, len(df5)):

            current_time = df5.index[i]

            # =====================================
            # ENTRY WINDOW → 09:45 to 13:30
            # =====================================

            if (
                current_time.time() < pd.to_datetime("09:45").time()
                or
                current_time.time() > pd.to_datetime("13:30").time()
            ):
                continue

            # =====================================
            # ALL 15M CANDLES BEFORE CURRENT 5M TIME
            # =====================================

            df15_valid = df15[
                df15.index <= current_time
            ]

            valid_15m_times = []

            # =====================================
            # 15M CHECK FIRST
            # =====================================

            for idx, row15 in df15_valid.iterrows():

                # Ignore 09:30 and before
                if idx.time() <= pd.to_datetime("09:30").time():
                    continue

                try:
                    o = float(row15["Open"])
                    h = float(row15["High"])
                    l = float(row15["Low"])
                    c = float(row15["Close"])
                    v = float(row15["Volume"])
                    vwap = float(row15["vwap"])

                except:
                    continue

                candle_range = h - l

                if candle_range <= 0:
                    continue

                body = abs(c - o)

                # =====================================
                # FULL 15M CONDITIONS
                # =====================================

                cond1 = v > 500000

                cond2 = (c * v) > 150000000

                range_pct = (candle_range / o) * 100
                cond3 = range_pct > 1

                body_pct = (body / o) * 100
                cond4 = body_pct > 0.6

                cond5 = c > vwap

                cond6 = (
                    v > df15["Volume"].mean() * 1.5
                )

                cond7 = c > o

                if (
                    cond1 and cond2 and cond3
                    and cond4 and cond5
                    and cond6 and cond7
                ):
                    valid_15m_times.append(idx)

            # =====================================
            # NO 15M → NO TRADE
            # =====================================

            if not valid_15m_times:
                continue

            # LAST VALID 15M SIGNAL
            trigger_time = valid_15m_times[-1]

            last15 = df15.loc[trigger_time]

            # =====================================
            # NO SAME CANDLE ENTRY
            # =====================================

            if current_time <= trigger_time:
                continue

            # =====================================
            # ENTRY MUST BE WITHIN 60 MIN
            # =====================================

            if (
                current_time - trigger_time
            ) > pd.Timedelta(minutes=60):
                continue

            # =====================================
            # NOW CHECK 5M ENTRY
            # =====================================

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            try:
                # VWAP Pullback
                condA = (
                    row["Low"] <= row["vwap"] * 1.002
                    and
                    row["Close"] > row["vwap"]
                )

                # Breakout Candle
                condB = (
                    row["Close"] > prev["High"]
                    and
                    row["Close"] > row["Open"]
                )

                if not condA:
                    continue

                if not condB:
                    continue

                # =====================================
                # ENTRY / SL / TARGET
                # =====================================

                entry = float(row["Close"])
                sl = float(row["vwap"])

                # Minimum SL Filter
                min_risk = entry * 0.003
                actual_risk = entry - sl

                if actual_risk < min_risk:
                    continue

                target = entry + (actual_risk * 2)

                # =====================================
                # RESULT CHECK
                # =====================================

                result = "OPEN"

                for j in range(i + 1, len(df5)):
                    future = df5.iloc[j]

                    if future["Low"] <= sl:
                        result = "LOSS"
                        break

                    elif future["High"] >= target:
                        result = "WIN"
                        break

                # =====================================
                # FINAL RETURN
                # =====================================

                return {
                    "stock": stock,
                    "radar": True,
                    "entry": True,
                    "t15": str(trigger_time),
                    "t5": str(current_time),
                    "entry_price": round(entry, 2),
                    "sl": round(sl, 2),
                    "target": round(target, 2),
                    "result": result
                }

            except Exception as e:
                print("5M ERROR:", e)
                continue

        # =====================================
        # ONLY RADAR FOUND / NO ENTRY
        # =====================================

        if len(valid_15m_times) > 0:
            return {
                "stock": stock,
                "radar": True,
                "entry": False,
                "t15": str(valid_15m_times[-1]),
                "t5": None,
                "entry_price": None,
                "sl": None,
                "target": None,
                "result": "WAITING FOR 5M"
            }

        # =====================================
        # NO SIGNAL
        # =====================================

        return {
            "stock": stock,
            "radar": False,
            "entry": False,
            "t15": None,
            "t5": None,
            "entry_price": None,
            "sl": None,
            "target": None,
            "result": "NO TRADE"
        }

    except Exception as e:
        print("FIND TRADE ERROR:", e)

        return {
            "stock": stock,
            "radar": False,
            "entry": False,
            "t15": None,
            "t5": None,
            "entry_price": None,
            "sl": None,
            "target": None,
            "result": "ERROR"
        }


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
