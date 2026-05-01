import os
import re
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request

BOT_TOKEN = "8218143624:AAGr75U7tVRiXKES5WIJneD6MotImx66qis"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ================= STOCK LIST =================

FNO_STOCKS = ["BHEL.NS","ADANIGREEN.NS","RELIANCE.NS","TCS.NS"]  # add full list

# ================= CACHE =================

DATA_15 = {}
DATA_5 = {}

# ================= TELEGRAM =================

def send(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage",
                  json={"chat_id": chat_id, "text": text})

def send_bulk(chat_id, messages):
    chunk = ""
    for m in messages:
        if len(chunk) + len(m) > 3500:
            send(chat_id, chunk)
            chunk = ""
        chunk += m + "\n\n"
    if chunk:
        send(chat_id, chunk)

# ================= VWAP =================

def add_vwap(df):
    df = df.copy()
    df["date"] = df.index.date

    out = []
    for _, g in df.groupby("date"):
        tp = (g["High"]+g["Low"]+g["Close"]) / 3
        v = (tp*g["Volume"]).cumsum() / g["Volume"].cumsum()
        out.append(v)

    df["VWAP"] = pd.concat(out)
    return df.drop(columns=["date"])

# ================= LOAD DATA =================

def load_symbol(symbol):
    try:
        df15 = yf.download(symbol, interval="15m", period="30d", progress=False)
        df5 = yf.download(symbol, interval="5m", period="30d", progress=False)

        for df in [df15, df5]:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")

        DATA_15[symbol] = add_vwap(df15)
        DATA_5[symbol] = add_vwap(df5)

        print("Loaded:", symbol)

    except Exception as e:
        print("Error:", symbol, e)

def preload():
    threads = []
    for s in FNO_STOCKS:
        t = threading.Thread(target=load_symbol, args=(s,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("✅ ALL DATA LOADED")

# ================= RADAR =================

def find_radars(df):
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()
    out = []

    for i in range(19, len(df)):
        r = df.iloc[i]

        if pd.isna(r["VOL_SMA"]):
            continue

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > 500000
            and r["Volume"] > 2*r["VOL_SMA"]
            and (r["Close"]-r["Open"]) / r["Open"] > 0.006
        ):
            out.append(df.index[i] + pd.Timedelta(minutes=15))

    return out

# ================= TRADE =================

def find_trade(df, radar_time):
    df = df[df.index > radar_time]

    for i in range(1, len(df)):
        r = df.iloc[i]
        p = df.iloc[i-1]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        score = 0
        if r["Low"] <= r["VWAP"]*1.002 and r["Close"] > r["VWAP"]: score+=1
        if r["Close"] > p["High"]: score+=1
        if r["Volume"] > p["Volume"]*1.2: score+=1
        if r["Close"] > r["Open"]: score+=1

        if score < 4:
            continue

        entry = round(r["High"],2)
        sl = round(p["VWAP"],2)

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk/entry <= 0.012):
            continue

        tgt = round(entry + risk*2,2)

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
            "time": r.name.strftime("%H:%M"),
            "entry": entry,
            "sl": sl,
            "target": tgt,
            "result": result,
            "score": f"{score}/5"
        }

    return None

# ================= PROCESS =================

def process_day(symbol, date):
    df15 = DATA_15.get(symbol)
    df5 = DATA_5.get(symbol)

    if df15 is None or df5 is None:
        return None

    df15 = df15[df15.index.date == pd.to_datetime(date).date()]
    df5 = df5[df5.index.date == pd.to_datetime(date).date()]

    radars = find_radars(df15)

    for r in radars:
        trade = find_trade(df5, r)

        if trade:
            return {
                "symbol": symbol,
                "radar": r.strftime("%H:%M"),
                "trade": trade
            }

    return None

# ================= FORMAT =================

def fmt(r):
    t = r["trade"]

    return (
        f"📊 {r['symbol']}\n"
        f"15M: {r['radar']}\n"
        f"5M: {t['time']}\n"
        f"Score: {t['score']}\n"
        f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
        f"Result: {t['result']}"
    )

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text","").upper().strip()

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, "⚡ FAST SCAN RUNNING")

        results = []

        for s in FNO_STOCKS:
            r = process_day(s, text)
            if r:
                results.append(fmt(r))

        if results:
            send_bulk(chat_id, results)
        else:
            send(chat_id, "No setup")

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

    return "ok"

@app.route("/")
def home():
    return "BOT RUNNING"

if __name__ == "__main__":
    preload()   # 🔥 KEY STEP
    app.run(host="0.0.0.0", port=PORT)
