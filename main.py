import os
import re
import time
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request
from datetime import datetime

# ================= CONFIG =================

BOT_TOKEN = "8218143624:AAGr75U7tVRiXKES5WIJneD6MotImx66qis"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

LAST_REQUEST = {}

# ================= UTILS =================

def is_duplicate(chat_id, text):
    key = f"{chat_id}:{text}"
    now = time.time()
    if key in LAST_REQUEST and now - LAST_REQUEST[key] < 5:
        return True
    LAST_REQUEST[key] = now
    return False


def send(chat_id, text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20
        )
    except:
        pass


def set_webhook():
    try:
        requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    except:
        pass

# ================= DATA =================

def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="30d", progress=False)

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index)

    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("Asia/Kolkata")
    except:
        pass

    return df


def session_filter(df):
    return df.between_time("09:45", "15:30")


def filter_date(df, date):
    d = pd.to_datetime(date).date()
    df = df[df.index.date == d]
    return df if not df.empty else None

# ================= INSTITUTIONAL VWAP =================

def vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

# ================= 15M RADAR =================

def find_15m(df):
    df = df.copy()
    df["VWAP"] = vwap(df)
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(20, len(df)):
        r = df.iloc[i]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA"]):
            continue

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > r["VOL_SMA"] * 1.5
            and r["Close"] > r["Open"]
        ):
            radars.append(df.index[i] + pd.Timedelta(minutes=15))

    return radars

# ================= 5M TRADE =================

def find_5m(df, radar_time):
    df = df[df.index > radar_time].copy()
    if df.empty:
        return None

    df["VWAP"] = vwap(df)

    for i in range(1, len(df)):
        r = df.iloc[i]
        p = df.iloc[i - 1]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        score = 0

        if r["Low"] <= r["VWAP"] * 1.002 and r["Close"] > r["VWAP"]:
            score += 1

        if r["Close"] > p["High"]:
            score += 1

        if r["Close"] > r["Open"]:
            score += 1

        if r["Volume"] > p["Volume"] * 1.2:
            score += 1

        if score < 4:
            continue

        entry = round(r["High"], 2)

        # ================= FIXED SL LOGIC =================
        vwap_value = r["VWAP"]

        sl = round(
            min(
                vwap_value,
                r["Low"] - (r["High"] - r["Low"]) * 0.1
            ),
            2
        )

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk / entry <= 0.015):
            continue

        target = round(entry + (risk * 2), 2)

        result = "OPEN"

        for j in range(i + 1, len(df)):
            nxt = df.iloc[j]

            if nxt.name.time() > pd.to_datetime("15:30").time():
                break

            if nxt["Low"] <= sl:
                result = "LOSS"
                break

            if nxt["High"] >= target:
                result = "WIN"
                break

        return {
            "time": df.index[i],
            "entry": entry,
            "sl": sl,
            "target": target,
            "result": result,
            "score": f"{score}/5"
        }

    return None

# ================= BACKTEST =================

def scan_stock(symbol, date=None):
    df15 = get_data(symbol, "15m")
    df5 = get_data(symbol, "5m")

    if df15 is None:
        return None

    df15 = session_filter(df15)

    if date:
        df15 = filter_date(df15, date)

    if df15 is None:
        return None

    radars = find_15m(df15)

    if not radars:
        return None

    radar_time = radars[0]   # 1 TRADE PER DAY

    trade = None

    if df5 is not None:
        temp5 = filter_date(df5, radar_time.date())
        if temp5 is not None:
            trade = find_5m(temp5, radar_time)

    return {
        "symbol": symbol,
        "radar": radar_time,
        "trade": trade
    }

# ================= RANGE =================

def run_range(symbol, d1, d2):
    results = []

    for d in pd.date_range(d1, d2):
        r = scan_stock(symbol, str(d.date()))
        if r:
            results.append(r)

    return results

# ================= FORMAT =================

def fmt(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']}\n"

    if r["trade"]:
        t = r["trade"]
        msg += f"5M: {t['time']}\n"
        msg += f"Score: {t['score']}\n"
        msg += f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
        msg += f"Result: {t['result']}"
    else:
        msg += "5M: NO SETUP"

    return msg

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    if is_duplicate(chat_id, text):
        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()
        send(chat_id, f"📊 RANGE {sym}")

        for r in run_range(sym + ".NS", d1, d2):
            send(chat_id, fmt(r))

        return "ok"

    # SINGLE STOCK DATE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        r = scan_stock(sym + ".NS", d)

        if r:
            send(chat_id, fmt(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # DATE RADAR
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]

        stocks = ["ADANIGREEN.NS", "BHEL.NS", "RELIANCE.NS"]

        for s in stocks:
            r = scan_stock(s, d)
            if r:
                send(chat_id, f"{s} → {r['radar']}")

        return "ok"

    send(chat_id, "Command OK")
    return "ok"

# ================= RUN =================

@app.route("/")
def home():
    return "BACKTEST BOT RUNNING"

if __name__ == "__main__":
    print("🚀 STARTING BOT")
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)
