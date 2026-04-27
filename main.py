# FULL FINAL HYBRID VWAP TELEGRAM BOT
# RENDER FREE PLAN + TELEGRAM + LIVE + DATE + STOCK + RANGE SCAN

import os
import asyncio
import pandas as pd
import yfinance as yf

from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# =====================================================
# BOT TOKEN
# =====================================================

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")


# =====================================================
# FLASK KEEP ALIVE FOR RENDER FREE PLAN
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
# SAFE FLOAT
# =====================================================

def safe_float(value):
    try:
        return float(value)
    except:
        return None


# =====================================================
# WATCHLIST (SAMPLE CORE F&O LIST)
# You can expand this full list
# =====================================================

# =====================================================
# NSE F&O COMPLETE WATCHLIST (ALL 213 STOCKS)
# Cleaned + Yahoo Finance Format (.NS)
# Copy-Paste Ready for VWAP Scanner Bot
# =====================================================

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
# VWAP CALCULATION
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

        # -----------------------------
        # DOWNLOAD DATA
        # -----------------------------

        df15 = yf.download(
            stock,
            interval="15m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True
        )

        df5 = yf.download(
            stock,
            interval="5m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True
        )

        if len(df15) < 10 or len(df5) < 20:
            return None

        # timezone safe
        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert(
                "Asia/Kolkata"
            ).tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert(
                "Asia/Kolkata"
            ).tz_localize(None)

        df5 = calculate_vwap(df5)

        # -----------------------------
        # PREVIOUS DAY CLOSE
        # -----------------------------

        df_daily = yf.download(
            stock,
            interval="1d",
            period="5d",
            progress=False,
            auto_adjust=True
        )

        if len(df_daily) < 2:
            return None

        prev_close = safe_float(
            df_daily["Close"].iloc[-2]
        )

        if prev_close is None:
            return None

        # -----------------------------
        # 15m FILTER
        # -----------------------------

        df15["vol_sma_20"] = (
            df15["Volume"].rolling(20).mean()
        )

        valid_15m = []

        for idx, row in df15.iterrows():

            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            o = safe_float(row["Open"])
            h = safe_float(row["High"])
            l = safe_float(row["Low"])
            c = safe_float(row["Close"])
            v = safe_float(row["Volume"])
            vol_sma = safe_float(row["vol_sma_20"])

            if None in [o, h, l, c, v]:
                continue

            candle_range = h - l
            if candle_range <= 0:
                continue

            body = abs(c - o)
            upper_wick = h - max(o, c)

            # Condition 1 → volume
            cond1 = v > 200000

            # Condition 2 → candle range
            range_pct = (candle_range / o) * 100
            cond2 = range_pct > 0.4

            # Condition 3 → body size
            body_pct = (body / o) * 100
            cond3 = body_pct > 0.4

            # Condition 4 → bullish candle
            cond4 = c > o

            # Condition 5 → volume spike
            cond5 = (
                vol_sma is not None
                and v > (1.5 * vol_sma)
            )

            # Condition 6 → wick quality
            cond6 = (
                (upper_wick / candle_range) < 0.5
            )

            # Condition 7 → gap filter
            gap_pct = abs(
                (o - prev_close) / prev_close
            ) * 100
            cond7 = gap_pct <= 1

            # Condition 8 → intraday move filter
            intraday_pct = abs(
                (c - o) / o
            ) * 100
            cond8 = intraday_pct <= 2

            if (
                cond1 and cond2 and cond3 and cond4
                and cond5 and cond6
                and cond7 and cond8
            ):
                valid_15m.append(idx)

        if not valid_15m:
            return None

        # -----------------------------
        # 5m VWAP SCORING
        # -----------------------------

        for i in range(2, len(df5)):

            current_time = df5.index[i]

            if current_time.time() < pd.to_datetime("09:45").time():
                continue

            if current_time.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            low = safe_float(row["Low"])
            high = safe_float(row["High"])
            close = safe_float(row["Close"])
            vol = safe_float(row["Volume"])
            vwap = safe_float(row["VWAP"])
            prev_high = safe_float(prev["High"])

            if None in [
                low, high, close,
                vol, vwap, prev_high
            ]:
                continue

            latest_trigger = None

            for trigger in valid_15m:
                if trigger < current_time:
                    diff = current_time - trigger

                    if diff <= pd.Timedelta(minutes=60):
                        latest_trigger = trigger

            if latest_trigger is None:
                continue

            if current_time <= latest_trigger:
                continue

            # -----------------------------
            # VWAP SCORE OUT OF 5
            # -----------------------------

            score = 0

            # 1. Clean VWAP touch
            if low <= vwap * 1.002:
                score += 1

            # 2. Strong rejection
            wick_rejection = (
                (close - low)
                > ((high - low) * 0.5)
            )
            if wick_rejection:
                score += 1

            # 3. Close above VWAP
            if close > vwap:
                score += 1

            # 4. Breakout above previous high
            if close > prev_high:
                score += 1

            # 5. Volume expansion
            avg_5m_vol = safe_float(
                df5["Volume"].rolling(20).mean().iloc[i]
            )

            if (
                avg_5m_vol is not None
                and vol > avg_5m_vol * 1.5
            ):
                score += 1

            if score < 4:
                continue

            # -----------------------------
            # ENTRY LOGIC
            # -----------------------------

            entry = round(close, 2)
            sl = round(vwap, 2)

            risk = entry - sl

            if risk <= 0:
                continue

            if risk < (entry * 0.003):
                continue

            target = round(
                entry + (risk * 2),
                2
            )

            result = "OPEN"

            for j in range(i + 1, len(df5)):
                future = df5.iloc[j]

                f_low = safe_float(future["Low"])
                f_high = safe_float(future["High"])

                if f_low is None or f_high is None:
                    continue

                if f_low <= sl:
                    result = "LOSS"
                    break

                if f_high >= target:
                    result = "WIN"
                    break

            return {
                "stock": stock,
                "trigger": str(latest_trigger),
                "entry_time": str(current_time),
                "score": f"{score}/5",
                "entry": entry,
                "sl": sl,
                "target": target,
                "result": result
            }

        return None

    except Exception as e:
        print(f"ERROR in {stock}: {str(e)}")
        return None


# =====================================================
# DATE SCAN
# =====================================================

def full_date_scan(date):
    results = []

    for stock in WATCHLIST:
        result = find_trade(stock, date)

        if result:
            results.append(result)

    return results


# =====================================================
# RANGE SCAN
# =====================================================

def range_scan(stock, start_date, end_date):
    results = []

    try:
        current = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        while current <= end:
            day = current.strftime("%Y-%m-%d")

            result = find_trade(stock, day)

            if result:
                results.append(result)

            current += timedelta(days=1)

        return results

    except Exception as e:
        print(f"RANGE SCAN ERROR: {str(e)}")
        return []


# =====================================================
# TELEGRAM HANDLER
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    # LIVE
    if text == "LIVE":
        today = datetime.now().strftime("%Y-%m-%d")

        await update.message.reply_text(
            f"Scanning LIVE F&O for {today}"
        )

        results = full_date_scan(today)

        if not results:
            await update.message.reply_text("❌ No trades found")
            return

        msg = f"🔥 LIVE RESULT - {today}\n\n"

        for r in results:
            msg += (
                f"{r['stock']}\n"
                f"Entry: {r['entry']} | "
                f"SL: {r['sl']} | "
                f"Target: {r['target']}\n"
                f"Result: {r['result']}\n\n"
            )

        await update.message.reply_text(msg)
        return

       # DATE ONLY
if len(text) == 10 and text.count("-") == 2:
    await update.message.reply_text(
        f"Scanning full F&O for {text}"
    )

    results = full_date_scan(text)

    if not results:
        await update.message.reply_text("❌ No trades found")
        return

    msg = f"🔥 DATE RESULT - {text}\n\n"

    for r in results:
        msg += (
            f"{r['stock']}\n"
            f"15m: {r['trigger']}\n"
            f"5m: {r['entry_time']}\n"
            f"VWAP Score: {r['score']}\n"
            f"Entry: {r['entry']} | "
            f"SL: {r['sl']} | "
            f"Target: {r['target']}\n"
            f"Result: {r['result']}\n\n"
        )

    await update.message.reply_text(msg)
    return

    # HELP
    await update.message.reply_text(
        "Use:\n"
        "LIVE\n"
        "2026-04-27\n"
        "VEDL 2026-04-27\n"
        "BHEL 2026-04-01 to 2026-04-20"
    )


# =====================================================
# START BOT
# =====================================================

async def main():
    print("BOT RUNNING...")

    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("TELEGRAM BOT STARTING...")

    await app.initialize()
    await app.start()

    if app.updater:
        await app.updater.start_polling(
            drop_pending_updates=True
        )

    print("TELEGRAM BOT STARTED SUCCESSFULLY")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
