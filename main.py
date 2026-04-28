import os
import re
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# =========================
# STATE
# =========================

RADAR_STATE = {}
TRADED_TODAY = set()

# =========================
# STOCK LIST (keep full list here)
# =========================

FNO_STOCKS = [
    "ADANIGREEN.NS",
    "BHEL.NS",
    "RELIANCE.NS",
    "TCS.NS"
]

# =========================
# TELEGRAM SEND
# =========================

def send(chat_id, text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print("Send error:", e)

# =========================
# WEBHOOK SET
# =========================

def set_webhook():
    url = f"{RENDER_URL}/webhook"
    try:
        r = requests.get(f"{BASE_URL}/setWebhook?url={url}")
        print("Webhook:", r.text)
    except Exception as e:
        print("Webhook error:", e)

# =========================
# DATA ENGINE
# =========================

def get_data(symbol, interval, period="5d"):
    df = yf.download(symbol, interval=interval, period=period, progress=False)
    if df is None or df.empty:
        return None
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.dropna()

def vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

# =========================
# 15M RADAR
# =========================

def check_15m(df):
    df = df.copy()
    df["VWAP"] = vwap(df)
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    for i in range(20, len(df)):
        c = df.iloc[i]
        open_p = c["Open"]

        if open_p <= 0:
            continue

        cond = (
            c["Volume"] > 500000 and
            c["Volume"] * c["Close"] > 150000000 and
            ((c["High"] - c["Low"]) / open_p) * 100 > 0.6 and
            (abs(c["Close"] - c["Open"]) / open_p) * 100 > 0.6 and
            c["Close"] > c["VWAP"] and
            c["Volume"] > 2 * c["VOL_SMA20"] and
            c["Close"] > c["Open"]
        )

        if cond:
            return {
                "time": df.index[i],
                "close": float(c["Close"])
            }

    return None

# =========================
# 5M TRADE
# =========================

def check_5m(df, radar_time):
    df = df[df.index > radar_time]
    if df.empty:
        return None

    df = df.copy()
    df["VWAP"] = vwap(df)

    for i in range(len(df)):
        c = df.iloc[i]

        if c["Low"] <= c["VWAP"] <= c["High"] and c["Close"] > c["Open"]:

            entry = c["High"]
            sl = c["Low"]
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

# =========================
# SCAN STOCK
# =========================

def scan_stock(symbol):
    if symbol in TRADED_TODAY:
        return None

    df15 = get_data(symbol, "15m")
    if df15 is None:
        return None

    radar = check_15m(df15)
    if not radar:
        return None

    RADAR_STATE[symbol] = radar

    df5 = get_data(symbol, "5m")
    trade = check_5m(df5, radar["time"]) if df5 is not None else None

    if trade:
        TRADED_TODAY.add(symbol)

    return {
        "symbol": symbol,
        "radar": radar,
        "trade": trade
    }

# =========================
# FULL SCAN
# =========================

def scan_all():
    results = []
    for s in FNO_STOCKS:
        r = scan_stock(s)
        if r:
            results.append(r)
    return results

# =========================
# BACKTEST SINGLE STOCK
# =========================

def backtest_stock(symbol, date):
    return scan_stock(symbol)

# =========================
# BACKTEST RANGE (SIMPLIFIED)
# =========================

def backtest_range(symbol, start, end):
    return [scan_stock(symbol)]

# =========================
# FORMAT RESULT
# =========================

def format_result(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']['time']}\n"

    if r.get("trade"):
        t = r["trade"]
        msg += f"5M: {t['time']}\nEntry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
    else:
        msg += "RADAR ACTIVE (waiting 5M)\n"

    return msg

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").upper().strip()

    print("CMD:", text)

    # =========================
    # 1 LIVE
    # =========================
    if text == "LIVE":
        send(chat_id, "📡 LIVE SCANNING FNO...")
        results = scan_all()

        for r in results:
            send(chat_id, format_result(r))

        return "ok"

    # =========================
    # 2 RADAR TODAY
    # =========================
    if text == "RADAR TODAY":
        send(chat_id, "📊 RADAR ONLY SCAN...")
        results = scan_all()

        for r in results:
            if r.get("radar"):
                send(chat_id, f"{r['symbol']} → {r['radar']['time']}")

        return "ok"

    # =========================
    # 3 DATE (FULL SCAN)
    # =========================
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, f"📅 SCANNING FULL FNO FOR {text}")
        results = scan_all()

        for r in results:
            send(chat_id, format_result(r))

        return "ok"

    # =========================
    # 4 STOCK + DATE
    # =========================
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, date = text.split()
        symbol = sym + ".NS"

        send(chat_id, f"📊 SCANNING {symbol}")

        r = scan_stock(symbol)
        if r:
            send(chat_id, format_result(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # =========================
    # 5 STOCK RANGE
    # =========================
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        parts = text.split()
        symbol = parts[0] + ".NS"

        send(chat_id, f"📅 RANGE SCAN {symbol}")

        results = backtest_range(symbol, parts[1], parts[3])

        for r in results:
            send(chat_id, format_result(r))

        return "ok"

    # =========================
    # 6 DATE RADAR ONLY
    # =========================
    if text.endswith("RADAR") and re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        send(chat_id, "📡 RADAR ONLY MODE")

        results = scan_all()
        for r in results:
            if r.get("radar"):
                send(chat_id, f"{r['symbol']} → {r['radar']['time']}")

        return "ok"

    # =========================
    # DEFAULT
    # =========================
    send(chat_id, "Unknown command")
    return "ok"

# =========================
# HOME
# =========================

@app.route("/")
def home():
    return "BOT RUNNING"

# =========================
# START
# =========================

if __name__ == "__main__":
    print("🚀 BOT V3 STARTED")

    set_webhook()

    app.run(host="0.0.0.0", port=PORT)
