import os
import re
import time
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request
from datetime import datetime

# ================= CONFIG =================

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
RENDER_URL = "https://your-url.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

# Delay for heavy scan (IMPORTANT for 200 stocks)
DATE_SCAN_DELAY = 1      # per stock delay
RADAR_DELAY = 0.5

app = Flask(__name__)

# ================= SEND =================

def send(chat_id, text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20
        )
    except Exception as e:
        print("Send Error:", e)

# ================= DATA =================

def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="30d", progress=False)

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    return df[["Open","High","Low","Close","Volume"]].dropna()

def to_ist(df):
    if df is None:
        return None

    df.index = pd.to_datetime(df.index)

    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")

        df.index = df.index.tz_convert("Asia/Kolkata")
    except:
        pass

    return df

def session_filter(df):
    try:
        df = df.between_time("09:45", "15:30")
        return df if not df.empty else None
    except:
        return None

def filter_date(df, d):
    d = pd.to_datetime(d).date()
    df = df[df.index.date == d]
    return df if not df.empty else None

def vwap(df):
    tp = (df["High"]+df["Low"]+df["Close"])/3
    return (tp*df["Volume"]).cumsum()/df["Volume"].cumsum()

# ================= 15M RADAR =================

def find_15m(df):
    df["VWAP"] = vwap(df)
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(19, len(df)):
        r = df.iloc[i]

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA"]):
            continue

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > 500000
            and r["Volume"] > 2 * r["VOL_SMA"]
            and (r["Close"] - r["Open"]) / r["Open"] > 0.006
        ):
            radars.append({
                "time": df.index[i] + pd.Timedelta(minutes=15)
            })

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

        # Entry time window
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
        sl = round(p["VWAP"], 2)

        risk = entry - sl

        if risk <= 0:
            continue

        if not (0.003 <= risk/entry <= 0.012):
            continue

        target = round(entry + risk * 2, 2)

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
            "time": df.index[i] + pd.Timedelta(minutes=5),
            "entry": entry,
            "sl": sl,
            "target": target,
            "result": result,
            "score": f"{score}/5"
        }

    return None

# ================= CORE LOGIC =================

def scan_stock(symbol, date):
    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return None

    df15 = session_filter(df15)
    if df15 is None:
        return None

    df15 = filter_date(df15, date)
    if df15 is None:
        return None

    radars = find_15m(df15)

    if not radars:
        return None

    # IMPORTANT LOGIC: first valid trade only
    for radar in radars:

        trade = None

        if df5 is not None:
            d5 = filter_date(df5, radar["time"].strftime("%Y-%m-%d"))

            if d5 is not None:
                trade = find_5m(d5, radar["time"])

        if trade:
            return {
                "symbol": symbol,
                "radar": radar,
                "trade": trade
            }

    return None

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
    msg += f"15M: {r['radar']['time'].strftime('%Y-%m-%d %H:%M')}\n"

    if r["trade"]:
        t = r["trade"]

        msg += f"5M: {t['time'].strftime('%Y-%m-%d %H:%M')}\n"
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

    # ================= DATE =================
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):

        send(chat_id, f"📅 SCANNING {text}")

        for s in FNO_STOCKS:
            r = scan_stock(s, text)

            if r:
                send(chat_id, fmt(r))

            time.sleep(DATE_SCAN_DELAY)

        return "ok"

    # ================= SINGLE =================
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):

        sym, d = text.split()
        symbol = sym + ".NS"

        r = scan_stock(symbol, d)

        if r:
            send(chat_id, fmt(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # ================= RANGE =================
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):

        sym, d1, _, d2 = text.split()

        send(chat_id, f"📊 RANGE SCAN {sym}")

        results = run_range(sym + ".NS", d1, d2)

        for r in results:
            send(chat_id, fmt(r))

        return "ok"

    # ================= RADAR =================
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):

        d = text.split()[0]

        send(chat_id, f"📊 RADAR {d}")

        for s in FNO_STOCKS:
            df15 = to_ist(get_data(s, "15m"))

            if df15 is None:
                continue

            df15 = session_filter(df15)
            df15 = filter_date(df15, d)

            if df15 is None:
                continue

            radars = find_15m(df15)

            for r in radars:
                send(chat_id, f"{s} → {r['time'].strftime('%H:%M')}")

            time.sleep(RADAR_DELAY)

        return "ok"

    send(chat_id, "Command OK")
    return "ok"

@app.route("/")
def home():
    return "BOT RUNNING"

if __name__ == "__main__":
    requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)
