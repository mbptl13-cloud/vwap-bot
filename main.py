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
    "BHEL.NS",
    "VEDL.NS",
    "ADANIGREEN.NS",
    "RELIANCE.NS",
    "SBIN.NS",
    "ICICIBANK.NS",
    "HDFCBANK.NS",
    "TATASTEEL.NS",
    "TATAPOWER.NS",
    "BAJFINANCE.NS",
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
    elif " TO " in text:
        try:
            parts = text.split()
            stock = parts[0] + ".NS"
            start_date = parts[1]
            end_date = parts[3]

            await update.message.reply_text(
                f"Scanning {stock} from {start_date} to {end_date}..."
            )

            current = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            results = []

            while current <= end_dt:
                day = current.strftime("%Y-%m-%d")
                result = find_trade(stock, day)
                if result:
                    results.append(result)
                current += timedelta(days=1)

            if not results:
                await update.message.reply_text("❌ No trades found")
                return

            msg = f"🔥 RANGE RESULT - {stock}

"
            for r in results:
                msg += (
                    f"{r['stock']}
"
                    f"15M Count: {r['valid_15m_count']}
"
                    f"15M Trigger: {r['trigger_times']}

"
                )

            await update.message.reply_text(msg)
            return

        except Exception:
            await update.message.reply_text("❌ Invalid range format")
            return

    elif len(text.split()) == 2 and len(text.split()[1]) == 10 and text.split()[1].count("-") == 2 and text.split()[1] != "15M":
        stock = text.split()[0] + ".NS"
        scan_date = text.split()[1]
        await update.message.reply_text(f"Scanning {stock} for {scan_date}...")
        result = find_trade(stock, scan_date)

        if not result:
            await update.message.reply_text("❌ No trade found")
            return

        msg = (
            f"🔥 STOCK RESULT

"
            f"{result['stock']}
"
            f"15M Count: {result['valid_15m_count']}
"
            f"15M Trigger: {result['trigger_times']}
"
        )

        await update.message.reply_text(msg)
        return

    elif " TO " in text:
        try:
            parts = text.split()
            stock = parts[0] + ".NS"
            start_date = parts[1]
            end_date = parts[3]

            await update.message.reply_text(
                f"Scanning {stock} from {start_date} to {end_date}..."
            )

            current = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            results = []

            while current <= end_dt:
                day = current.strftime("%Y-%m-%d")
                result = find_trade(stock, day)
                if result:
                    results.append(result)
                current += timedelta(days=1)

            if not results:
                await update.message.reply_text("❌ No trades found")
                return

            msg = f"🔥 RANGE RESULT - {stock}

"
            for r in results:
                msg += (
                    f"Date Trigger: {r['trigger_times']}
"
                    f"15M Count: {r['valid_15m_count']}

"
                )

            await update.message.reply_text(msg)
            return

        except Exception:
            await update.message.reply_text("❌ Invalid range format")
            return

    elif len(text) == 10 and text.count("-") == 2:
        await update.message.reply_text(f"Scanning full F&O for {text}...")
        results = full_date_scan(text)
    else:
        await update.message.reply_text(
            "Use:
LIVE
2026-04-06
BHEL 2026-04-06
BHEL 2026-04-06 to 2026-04-20
2026-04-06 15M"
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
