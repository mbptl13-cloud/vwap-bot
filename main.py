import os
import re
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request

BOT_TOKEN = "8695080537:AAFolODguF8s1z88s_57HTVModIrmGojlno"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

FNO_STOCKS = ["ADANIGREEN.NS", "BHEL.NS", "RELIANCE.NS", "TCS.NS"]

# ================= TELEGRAM =================

def send(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage",
                      json={"chat_id": chat_id, "text": text})
    except:
        pass

# ================= DATA =================

def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="30d", progress=False)

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    df = df[["Open","High","Low","Close","Volume"]].dropna()

    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("Asia/Kolkata")

    return df

# ================= VWAP (DAILY RESET) =================

def add_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    df["TPV"] = tp * df["Volume"]

    df["CUM_TPV"] = df.groupby(df.index.date)["TPV"].cumsum()
    df["CUM_VOL"] = df.groupby(df.index.date)["Volume"].cumsum()

    df["VWAP"] = df["CUM_TPV"] / df["CUM_VOL"]
    return df

# ================= 15M RADAR =================

def find_15m(df):
    df = add_vwap(df.copy())
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(20, len(df)):
        r = df.iloc[i]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA20"]):
            continue

        volume_cond = r["Volume"] > 500000
        turnover_cond = (r["Close"] * r["Volume"]) > 150000000

        range_pct = ((r["High"] - r["Low"]) / r["Open"]) * 100
        body_pct = (abs(r["Close"] - r["Open"]) / r["Open"]) * 100

        range_cond = range_pct > 1
        body_cond = body_pct > 0.6

        vwap_cond = r["Close"] > r["VWAP"]
        vol_spike = r["Volume"] > (2 * r["VOL_SMA20"])
        bullish = r["Close"] > r["Open"]

        if all([volume_cond, turnover_cond, range_cond,
                body_cond, vwap_cond, vol_spike, bullish]):
            
            radars.append(r.name + pd.Timedelta(minutes=15))

    return radars

# ================= 5M TRADE =================

def find_5m(df, radar_time):
    df = add_vwap(df.copy())

    # only after radar
    df = df[df.index > radar_time]
    if df.empty:
        return None

    for i in range(1, len(df)):
        r = df.iloc[i]
        p = df.iloc[i-1]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("15:30").time()):
            continue

        score = 0

        if r["Low"] <= r["VWAP"] * 1.003: score += 1
        if r["Close"] > p["High"]: score += 1
        if r["Close"] > r["Open"]: score += 1
        if r["Volume"] > p["Volume"] * 1.1: score += 1

        if score < 3:
            continue

        entry = round(r["High"], 2)

        sl = round(min(
            r["VWAP"],
            r["Low"] - (r["High"] - r["Low"]) * 0.15
        ), 2)

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk/entry <= 0.02):
            continue

        target = round(entry + risk*2, 2)

        result = "OPEN"

        for j in range(i+1, len(df)):
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
            "time": r.name,
            "entry": entry,
            "sl": sl,
            "target": target,
            "result": result,
            "score": f"{score}/5"
        }

    return None

# ================= CORE =================

def scan_stock(sym, date):
    df15 = get_data(sym, "15m")
    df5 = get_data(sym, "5m")

    if df15 is None:
        return None

    df15 = df15[df15.index.date == pd.to_datetime(date).date()]
    if df15.empty:
        return None

    radars = find_15m(df15)

    if not radars:
        return {"symbol": sym, "radar": f"{date} → NO RADAR", "trade": None}

    radar = radars[0]

    trade = None
    if df5 is not None:
        df5 = df5[df5.index.date == radar.date()]
        trade = find_5m(df5, radar)

    return {"symbol": sym, "radar": radar, "trade": trade}

# ================= RANGE =================

def run_range(sym, d1, d2):
    res = []
    for d in pd.date_range(d1, d2):
        r = scan_stock(sym, str(d.date()))
        res.append(r)
    return res

# ================= FORMAT =================

def fmt(r):
    if isinstance(r["radar"], str):
        return f"{r['symbol']} → {r['radar']}"

    msg = f"📊 {r['symbol']}\n15M: {r['radar']}\n"

    if r["trade"]:
        t = r["trade"]
        msg += f"5M: {t['time']}\nEntry: {t['entry']} SL: {t['sl']} TG: {t['target']}\nResult: {t['result']}"
    else:
        msg += "5M: NO SETUP"

    return msg

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text","").upper()

    if text == "/START":
    send(chat_id,
"""🤖 FNO BACKTEST BOT

Available Commands:

1️⃣ DATE SCAN
2026-04-27

2️⃣ STOCK DATE
BHEL 2026-04-27

3️⃣ RANGE
ADANIGREEN 2026-04-01 TO 2026-04-10

4️⃣ RADAR
2026-04-27 RADAR
""")
        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym,d1,_,d2 = text.split()
        send(chat_id, f"📊 RANGE {sym}")
        for r in run_range(sym+".NS", d1, d2):
            send(chat_id, fmt(r))
        return "ok"

    # SYMBOL DATE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym,d = text.split()
        send(chat_id, fmt(scan_stock(sym+".NS", d)))
        return "ok"

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        for s in FNO_STOCKS:
            send(chat_id, fmt(scan_stock(s, text)))
        return "ok"

    # RADAR
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]
        send(chat_id, f"📡 RADAR {d}")
        for s in FNO_STOCKS:
            r = scan_stock(s, d)
            if r and not isinstance(r["radar"], str):
                send(chat_id, f"{s} → {r['radar']}")
        return "ok"

    return "ok"

# ================= RUN =================

@app.route("/")
def home():
    return "RUNNING"

if __name__ == "__main__":
    requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)
