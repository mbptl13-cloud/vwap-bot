import os
import re
import time
import threading
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
        df = df.between_time("09:45","15:30")
        return df if not df.empty else None
    except:
        return None

def filter_date(df, d):
    d = pd.to_datetime(d).date()
    df = df[df.index.date == d]
    return df if not df.empty else None

# ================= VWAP FIX =================

def calculate_vwap_intraday(df):
    df = df.copy()
    df["date"] = df.index.date

    vwap_list = []

    for d in df["date"].unique():
        temp = df[df["date"] == d].copy()

        tp = (temp["High"] + temp["Low"] + temp["Close"]) / 3
        vwap = (tp * temp["Volume"]).cumsum() / temp["Volume"].cumsum()

        vwap_list.append(vwap)

    return pd.concat(vwap_list)

# ================= RADAR =================

def find_15m(df):
    df = df.copy()
    df["VWAP"] = calculate_vwap_intraday(df)
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

# ================= TRADE =================

def find_5m(df, radar_time):
    df = df[df.index > radar_time].copy()
    if df.empty:
        return None

    df["VWAP"] = calculate_vwap_intraday(df)

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
        sl = round(p["VWAP"], 2)

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk / entry <= 0.012):
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

# ================= SCAN =================

def scan_stock(symbol, date):
    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None or df5 is None:
        return None

    df15 = session_filter(df15)
    if df15 is None:
        return None

    df15 = filter_date(df15, date)
    df5 = filter_date(df5, date)

    if df15 is None or df5 is None:
        return None

    radars = find_15m(df15)

    for r in radars:
        trade = find_5m(df5, r["time"])

        if trade:
            return {
                "symbol": symbol,
                "radar": r,
                "trade": trade
            }

    return None

# ================= FORMAT =================

def fmt(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']['time'].strftime('%Y-%m-%d %H:%M')}\n"

    t = r["trade"]
    msg += f"5M: {t['time'].strftime('%Y-%m-%d %H:%M')}\n"
    msg += f"Score: {t['score']}\n"
    msg += f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
    msg += f"Result: {t['result']}"

    return msg

# ================= COMMAND THREADS =================

def run_date(chat_id, date):
    send(chat_id, f"📅 SCANNING {date}...")

    for s in ["ADANIGREEN.NS","BHEL.NS","RELIANCE.NS","TCS.NS"]:
        r = scan_stock(s, date)
        if r:
            send(chat_id, fmt(r))

    send(chat_id, "✅ DONE")

def run_single(chat_id, sym, date):
    send(chat_id, f"📊 SCANNING {sym}")

    r = scan_stock(sym + ".NS", date)

    if r:
        send(chat_id, fmt(r))
    else:
        send(chat_id, "No setup")

def run_range(chat_id, sym, d1, d2):
    send(chat_id, f"📊 RANGE {sym}")

    for d in pd.date_range(d1, d2):
        r = scan_stock(sym + ".NS", str(d.date()))
        if r:
            send(chat_id, fmt(r))

    send(chat_id, "✅ DONE")

def run_radar(chat_id, date):
    send(chat_id, f"📊 RADAR {date}")

    for s in ["ADANIGREEN.NS","BHEL.NS","RELIANCE.NS","TCS.NS"]:
        df15 = to_ist(get_data(s, "15m"))
        df15 = session_filter(df15)
        df15 = filter_date(df15, date)

        if df15 is None:
            continue

        radars = find_15m(df15)

        for r in radars:
            send(chat_id, f"{s} → {r['time'].strftime('%H:%M')}")

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    print("RECEIVED:", text)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        threading.Thread(target=run_date, args=(chat_id, text)).start()
        return "ok"

    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        threading.Thread(target=run_single, args=(chat_id, sym, d)).start()
        return "ok"

    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()
        threading.Thread(target=run_range, args=(chat_id, sym, d1, d2)).start()
        return "ok"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]
        threading.Thread(target=run_radar, args=(chat_id, d)).start()
        return "ok"

    return "ok"

@app.route("/")
def home():
    return "BOT RUNNING"

if __name__ == "__main__":
    print("🚀 BACKTEST BOT RUNNING")
    requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)
