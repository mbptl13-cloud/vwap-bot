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
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# =========================================================
# AUTO WEBHOOK SETUP (CRITICAL FIX)
# =========================================================

def set_webhook():
    url = f"{RENDER_URL}/{BOT_TOKEN}"
    try:
        import requests
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={url}"
        )
        print("Webhook set:", r.text)
    except Exception as e:
        print("Webhook error:", e)

# =========================================================
# STOCK LIST (SHORT FOR SAFETY)
# =========================================================

FNO_STOCKS = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHEL.NS"]

# =========================================================
# DATA
# =========================================================

def download_data(symbol, interval="5m", period="5d"):
    try:
        df = yf.download(symbol, interval=interval, period=period, progress=False)
        if df is None or df.empty:
            return None
        return df.dropna()
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
# 15M LOGIC
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
# 5M LOGIC
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
    out = []
    for s in FNO_STOCKS:
        r = scan_stock(s)
        if r:
            out.append(r)
    return out

# =========================================================
# FORMAT
# =========================================================

def format_result(r):
    msg = f"📊 {r['symbol']}\n15M: {r['radar']['time']}\n"

    if r.get("trade"):
        t = r["trade"]
        msg += f"5M: {t['time']}\nEntry: {t['entry']}\nSL: {t['sl']}\nTarget: {t['target']}"
    else:
        msg += "RADAR ACTIVE"

    return msg

# =========================================================
# TELEGRAM HANDLERS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("START TRIGGERED")
    await update.message.reply_text("🚀 Bot is LIVE (v2 stable)")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip().upper()
        print("MESSAGE:", text)

        await update.message.reply_text(f"Processing: {text}")

        if text == "LIVE":
            res = full_scan()
            for r in res:
                await update.message.reply_text(format_result(r))
            return

        if text == "RADAR TODAY":
            res = full_scan()
            await update.message.reply_text("\n".join([r["symbol"] for r in res]))
            return

        if re.fullmatch(r"[A-Z]+\s\d{4}-\d{2}-\d{2}", text):
            stock = text.split()[0] + ".NS"
            r = scan_stock(stock)
            await update.message.reply_text(format_result(r) if r else "No setup")
            return

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\sRADAR", text):
            res = full_scan()
            await update.message.reply_text("\n".join([r["symbol"] for r in res]))
            return

        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            res = full_scan()
            for r in res:
                await update.message.reply_text(format_result(r))
            return

        await update.message.reply_text("Invalid command")

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("Error occurred")

# =========================================================
# APP SETUP
# =========================================================

telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT, handle))

# =========================================================
# WEBHOOK
# =========================================================

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    print("🔥 WEBHOOK HIT")   # <--- MUST SEE THIS

    data = request.get_json(force=True)
    print("DATA RECEIVED:", data)  # <--- ADD THIS TOO

    update = Update.de_json(data, bot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_app.process_update(update))

    return "ok"


@app.route("/")
def home():
    return "Bot v2 Running"

# =========================================================
# STARTUP
# =========================================================

if __name__ == "__main__":
    print("🚀 STARTING BOT v2")

    set_webhook()

    app.run(host="0.0.0.0", port=PORT)
