# FINAL ZERO-ERROR VWAP TELEGRAM BOT
# Commands Supported:
# LIVE
# 2026-04-06
# 2026-04-06 15M
# VEDL 2026-04-27
# VEDL 2026-04-21 to 2026-04-27

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
    filters,
)

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")

# ---------------- FLASK KEEP ALIVE ----------------
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


# ---------------- HELPERS ----------------
def safe_float(value):
    try:
        return float(value)
    except:
        return None


def calculate_vwap(df):
    df = df.copy()
    df["cum_vol"] = df["Volume"].cumsum()
    df["cum_vp"] = (df["Close"] * df["Volume"]).cumsum()
    df["VWAP"] = df["cum_vp"] / df["cum_vol"]
    return df


WATCHLIST = [
    "BHEL.NS",
    "VEDL.NS",
    "ADANIGREEN.NS",
    "RELIANCE.NS",
    "SBIN.NS",
    "ICICIBANK.NS",
    "HDFCBANK.NS",
    "TATAPOWER.NS",
    "TATASTEEL.NS",
    "INFY.NS",
]


# ---------------- MAIN STRATEGY ----------------
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

        if len(df15) < 5 or len(df5) < 10:
            return None

        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert("Asia/Kolkata").tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert("Asia/Kolkata").tz_localize(None)

        df5 = calculate_vwap(df5)

        valid_15m = []
        for idx, row in df15.iterrows():
            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            o = safe_float(row["Open"])
            c = safe_float(row["Close"])
            v = safe_float(row["Volume"])

            if None in [o, c, v]:
                continue

            if c > o and v > 100000:
                valid_15m.append(idx.strftime("%H:%M"))

        if not valid_15m:
            return None

        best_time = None
        best_score = 0
        best_entry = "-"
        best_sl = "-"
        best_target = "-"
        five_min_entry = "NO"

        for i in range(2, len(df5)):
            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            low = safe_float(row["Low"])
            high = safe_float(row["High"])
            close = safe_float(row["Close"])
            vwap = safe_float(row["VWAP"])
            prev_high = safe_float(prev["High"])

            if None in [low, high, close, vwap, prev_high]:
                continue

            score = 0

            if low <= vwap * 1.002:
                score += 1
            if close > vwap:
                score += 1
            if close > prev_high:
                score += 1

            if score > best_score:
                best_score = score
                best_time = df5.index[i].strftime("%H:%M")
                best_entry = round(close, 2)
                best_sl = round(vwap, 2)
                risk = best_entry - best_sl
                if risk > 0:
                    best_target = round(best_entry + (risk * 2), 2)

            if score >= 1:
                five_min_entry = "YES"

        return {
            "stock": stock,
            "valid_15m_count": len(valid_15m),
            "trigger_times": ", ".join(valid_15m),
            "five_min_entry": five_min_entry,
            "best_5m_time": best_time or "None",
            "best_score": f"{best_score}/3",
            "entry": best_entry,
            "sl": best_sl,
            "target": best_target,
        }

    except Exception as e:
        print("ERROR:", str(e))
        return None


def full_date_scan(date):
    results = []
    for stock in WATCHLIST:
        result = find_trade(stock, date)
        if result:
            results.append(result)
    return results


def range_scan(stock, start_date, end_date):
    results = []
    current = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    while current <= end:
        day = current.strftime("%Y-%m-%d")
        result = find_trade(stock, day)
        if result:
            result["date"] = day
            results.append(result)
        current += timedelta(days=1)

    return results


# ---------------- TELEGRAM ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()

    if text == "LIVE":
        await update.message.reply_text("Use:\nLIVE\n2026-04-06\n2026-04-06 15M\nVEDL 2026-04-27\nVEDL 2026-04-21 to 2026-04-27")
        return

    if len(text.split()) == 2 and text.split()[1] == "15M":
        scan_date = text.split()[0]
        results = full_date_scan(scan_date)

        if not results:
            await update.message.reply_text("❌ No 15M setups found")
            return

        msg = f"🔥 15M FILTER RESULT - {scan_date}\n\n"
        for r in results:
            msg += (
                f"{r['stock']}\n"
                f"15M Count: {r['valid_15m_count']}\n"
                f"15M Trigger: {r['trigger_times']}\n"
                f"5M Entry: {r['five_min_entry']}\n"
                f"5M Time: {r['best_5m_time']}\n\n"
            )

        await update.message.reply_text(msg)
        return

    if " TO " in text:
        parts = text.split()
        if len(parts) == 4:
            stock = parts[0] + ".NS"
            start_date = parts[1]
            end_date = parts[3]

            results = range_scan(stock, start_date, end_date)

            if not results:
                await update.message.reply_text("❌ No trades found")
                return

            msg = f"🔥 RANGE RESULT - {stock}\n\n"
            for r in results:
                msg += (
                    f"Date: {r['date']}\n"
                    f"15M Count: {r['valid_15m_count']}\n"
                    f"5M Entry: {r['five_min_entry']}\n"
                    f"5M Time: {r['best_5m_time']}\n\n"
                )

            await update.message.reply_text(msg)
            return

    parts = text.split()
    if len(parts) == 2 and len(parts[1]) == 10:
        stock = parts[0] + ".NS"
        date = parts[1]

        result = find_trade(stock, date)

        if not result:
            await update.message.reply_text("❌ No trade found")
            return

        msg = (
            f"{result['stock']}\n"
            f"15M Count: {result['valid_15m_count']}\n"
            f"15M Trigger: {result['trigger_times']}\n"
            f"5M Entry: {result['five_min_entry']}\n"
            f"5M Time: {result['best_5m_time']}\n"
            f"Score: {result['best_score']}\n"
            f"Entry: {result['entry']}\n"
            f"SL: {result['sl']}\n"
            f"TGT: {result['target']}"
        )

        await update.message.reply_text(msg)
        return

    if len(text) == 10 and text.count("-") == 2:
        results = full_date_scan(text)

        if not results:
            await update.message.reply_text("❌ No trades found")
            return

        msg = f"🔥 DATE RESULT - {text}\n\n"
        for r in results:
            msg += f"{r['stock']} | 15M: {r['trigger_times']} | 5M: {r['five_min_entry']}\n"

        await update.message.reply_text(msg)
        return

    await update.message.reply_text(
        "Use:\nLIVE\n2026-04-06\n2026-04-06 15M\nVEDL 2026-04-27\nVEDL 2026-04-21 to 2026-04-27"
    )


async def main():
    print("BOT RUNNING...")
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
    
