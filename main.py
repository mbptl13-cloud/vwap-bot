import os
import re
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# =========================
# STOCKS
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
    except:
        pass

# =========================
# WEBHOOK SET
# =========================

def set_webhook():
    try:
        requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    except:
        pass

# =========================
# TIMEZONE (SAFE)
# =========================

def to_ist(df):
    if df is None or df.empty:
        return None

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("Asia/Kolkata")
    except:
        pass

    return df

# =========================
# SESSION FILTER
# =========================

def session_filter(df):
    if df is None or df.empty:
        return None
    try:
        df = df.between_time("09:45", "13:30")
    except:
        return None
    return df if not df.empty else None

# =========================
# DATA
# =========================

def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="5d", progress=False)

    if df is None or df.empty:
        return None

    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.dropna()

def vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

# =========================
# DATE FILTER
# =========================

def filter_date(df, date):
    if df is None or df.empty:
        return None

    df = df.copy()
    df["date"] = df.index.date
    target = pd.to_datetime(date).date()

    df = df[df["date"] == target]
    return df.drop(columns=["date"])

# =========================
# 15M RADAR (CANDLE CLOSE FIX)
# =========================

def check_15m(df):
    df = session_filter(df)
    if df is None or len(df) < 20:
        return None

    df = df.copy()
    df["VWAP"] = vwap(df)
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    for i in range(20, len(df)):
        c = df.iloc[i]
        op = c["Open"]

        if op <= 0:
            continue

        cond = (
            c["Volume"] > 500000 and
            c["Volume"] * c["Close"] > 150000000 and
            ((c["High"] - c["Low"]) / op) * 100 > 0.6 and
            (abs(c["Close"] - c["Open"]) / op) * 100 > 0.6 and
            c["Close"] > c["VWAP"] and
            c["Volume"] > 2 * c["VOL_SMA20"] and
            c["Close"] > c["Open"]
        )

        if cond:
            radar_time = df.index[i] + timedelta(minutes=15)  # candle close fix

            return {
                "time": radar_time,
                "close": float(c["Close"])
            }

    return None

# =========================
# 5M TRADE
# =========================

def check_5m(df, radar_time):
    df = session_filter(df)

    if df is None or df.empty:
        return None

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

def scan_stock(symbol, date=None):

    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return None

    if date:
        df15 = filter_date(df15, date)
        df5 = filter_date(df5, date)

    radar = check_15m(df15)
    if not radar:
        return None

    trade = check_5m(df5, radar["time"]) if df5 is not None else None

    return {
        "symbol": symbol,
        "radar": radar,
        "trade": trade
    }

# =========================
# SCAN ALL
# =========================

def scan_all(date=None):
    results = []

    for s in FNO_STOCKS:
        r = scan_stock(s, date)
        if r:
            results.append(r)

    return results

# =========================
# FORMAT
# =========================

def format_result(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']['time']}\n"

    if r.get("trade"):
        t = r["trade"]
        msg += f"5M: {t['time']}\nEntry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
    else:
        msg += "RADAR ONLY\n"

    return msg

# =========================
# COMMAND PARSER (ALL FIXED)
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    today = datetime.now().strftime("%Y-%m-%d")

    # =========================
    # LIVE
    # =========================
    if text == "LIVE":
        send(chat_id, "📡 LIVE SCANNING")
        results = scan_all(date=today)

        for r in results:
            send(chat_id, format_result(r))

        return "ok"

    # =========================
    # RADAR TODAY
    # =========================
    if text == "RADAR TODAY":
        send(chat_id, "📊 RADAR TODAY")
        results = scan_all(date=today)

        for r in results:
            send(chat_id, f"{r['symbol']} → {r['radar']['time']}")

        return "ok"

    # =========================
    # DATE RADAR
    # =========================
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        date = text.replace(" RADAR", "")
        send(chat_id, f"📊 RADAR {date}")

        results = scan_all(date=date)

        for r in results:
            send(chat_id, f"{r['symbol']} → {r['radar']['time']}")

        return "ok"

    # =========================
    # DATE ONLY
    # =========================
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, f"📅 SCANNING {text}")
        results = scan_all(date=text)

        for r in results:
            send(chat_id, format_result(r))

        return "ok"

    # =========================
    # STOCK DATE
    # =========================
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, date = text.split()

        send(chat_id, f"📊 SCANNING {sym}")

        r = scan_stock(sym + ".NS", date)

        if r:
            send(chat_id, format_result(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # =========================
    # RANGE
    # =========================
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):

    sym, d1, _, d2 = text.split()
    symbol = sym + ".NS"

    send(chat_id, f"📊 RANGE SCANNING {sym}")

    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        send(chat_id, "No data")
        return "ok"

    d1 = pd.to_datetime(d1).date()
    d2 = pd.to_datetime(d2).date()

    found = False

    current = d1
    while current <= d2:

        date_str = current.strftime("%Y-%m-%d")

        temp15 = filter_date(df15, date_str)
        temp5 = filter_date(df5, date_str)

        radar = check_15m(temp15)

        if radar:
            trade = check_5m(temp5, radar["time"]) if temp5 is not None else None

            r = {
                "symbol": symbol,
                "radar": radar,
                "trade": trade
            }

            send(chat_id, format_result(r))
            found = True

        current += pd.Timedelta(days=1)

    if not found:
        send(chat_id, "No setups in range")

    return "ok"


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return "V8 FULL COMMAND ENGINE RUNNING"

# =========================
# START
# =========================

if __name__ == "__main__":
    print("🚀 V8 ENGINE STARTED")

    set_webhook()

    app.run(host="0.0.0.0", port=PORT)
