import os
import re
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request
from datetime import datetime

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ================= SEND =================

def send(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage",
                  json={"chat_id": chat_id, "text": text})

# ================= DATA =================

CACHE = {}

def get_data(symbol):
    if symbol in CACHE:
        return CACHE[symbol]

    df15 = yf.download(symbol, interval="15m", period="30d", progress=False)
    df5 = yf.download(symbol, interval="5m", period="30d", progress=False)

    if df15.empty or df5.empty:
        return None, None

    for df in [df15, df5]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")

    CACHE[symbol] = (df15, df5)
    return df15, df5

# ================= VWAP FIX =================

def add_vwap(df):
    df = df.copy()
    df["date"] = df.index.date

    vwap_list = []

    for d, group in df.groupby("date"):
        tp = (group["High"] + group["Low"] + group["Close"]) / 3
        vwap = (tp * group["Volume"]).cumsum() / group["Volume"].cumsum()
        vwap_list.append(vwap)

    df["VWAP"] = pd.concat(vwap_list)
    return df.drop(columns=["date"])

# ================= RADAR =================

def find_radars(df):
    df = add_vwap(df)
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(19, len(df)):
        r = df.iloc[i]

        if pd.isna(r["VOL_SMA"]):
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

def find_trade(df5, radar_time):
    df = add_vwap(df5)
    df = df[df.index > radar_time]

    for i in range(1, len(df)):
        r = df.iloc[i]
        p = df.iloc[i-1]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        score = 0
        if r["Low"] <= r["VWAP"] * 1.002 and r["Close"] > r["VWAP"]: score += 1
        if r["Close"] > p["High"]: score += 1
        if r["Close"] > r["Open"]: score += 1
        if r["Volume"] > p["Volume"] * 1.2: score += 1

        if score < 4:
            continue

        entry = round(r["High"], 2)
        sl = round(p["VWAP"], 2)

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk/entry <= 0.012):
            continue

        tgt = round(entry + risk*2, 2)

        result = "OPEN"

        for j in range(i+1, len(df)):
            nxt = df.iloc[j]

            if nxt.name.time() > pd.to_datetime("15:30").time():
                break

            if nxt["Low"] <= sl:
                result = "LOSS"
                break

            if nxt["High"] >= tgt:
                result = "WIN"
                break

        return {
            "time": r.name.strftime("%Y-%m-%d %H:%M"),
            "entry": entry,
            "sl": sl,
            "target": tgt,
            "result": result,
            "score": f"{score}/5"
        }

    return None

# ================= CORE LOGIC =================

def process_day(symbol, date):
    df15, df5 = get_data(symbol)
    if df15 is None:
        return None

    df15 = df15[df15.index.date == pd.to_datetime(date).date()]
    df5 = df5[df5.index.date == pd.to_datetime(date).date()]

    radars = find_radars(df15)

    for r in radars:
        trade = find_trade(df5, r["time"])

        if trade:
            return {
                "symbol": symbol,
                "radar": r["time"].strftime("%Y-%m-%d %H:%M"),
                "trade": trade
            }

    return None

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

    return msg

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "").upper().strip()

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, "📅 SCANNING...")

        for s in ["BHEL.NS", "ADANIGREEN.NS"]:
            r = process_day(s, text)
            if r:
                send(chat_id, fmt(r))

        return "ok"

    # SINGLE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        r = process_day(sym+".NS", d)

        if r:
            send(chat_id, fmt(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()

        for d in pd.date_range(d1, d2):
            r = process_day(sym+".NS", str(d.date()))
            if r:
                send(chat_id, fmt(r))

        return "ok"

    # RADAR ONLY
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]

        df15, _ = get_data("BHEL.NS")
        df15 = df15[df15.index.date == pd.to_datetime(d).date()]

        radars = find_radars(df15)

        for r in radars:
            send(chat_id, f"Radar → {r['time'].strftime('%H:%M')}")

        return "ok"

    return "ok"

@app.route("/")
def home():
    return "BOT RUNNING"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
