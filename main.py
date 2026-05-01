import os
import re
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

# ================= STOCK LIST =================

FNO_STOCKS = [
    "ADANIGREEN.NS","BHEL.NS","RELIANCE.NS","TCS.NS"
]

# ================= TELEGRAM =================

def send(chat_id, text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except:
        pass

# ================= DATA CACHE =================

CACHE = {}

def get_data(symbol):
    if symbol in CACHE:
        return CACHE[symbol]

    df15 = yf.download(symbol, interval="15m", period="30d", progress=False)
    df5  = yf.download(symbol, interval="5m", period="30d", progress=False)

    if df15.empty or df5.empty:
        return None, None

    df15.index = pd.to_datetime(df15.index).tz_localize("UTC").tz_convert("Asia/Kolkata")
    df5.index  = pd.to_datetime(df5.index).tz_localize("UTC").tz_convert("Asia/Kolkata")

    CACHE[symbol] = (df15, df5)
    return df15, df5

# ================= VWAP (FIXED) =================

def calculate_vwap(df):
    df = df.copy()
    df["date"] = df.index.date

    vwap_list = []

    for d in df["date"].unique():
        temp = df[df["date"] == d]

        tp = (temp["High"] + temp["Low"] + temp["Close"]) / 3
        vwap = (tp * temp["Volume"]).cumsum() / temp["Volume"].cumsum()

        vwap_list.extend(vwap)

    df["VWAP"] = vwap_list
    return df.drop(columns=["date"])

# ================= 15M RADAR =================

def find_radars(df15):
    df = calculate_vwap(df15)

    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(20, len(df)):
        r = df.iloc[i]

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA"]):
            continue

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > 2 * r["VOL_SMA"]
            and (r["Close"] - r["Open"]) / r["Open"] > 0.006
        ):
            radars.append(df.index[i] + pd.Timedelta(minutes=15))

    return radars

# ================= 5M TRADE =================

def find_trade(df5, radar_time):
    df = df5[df5.index > radar_time].copy()
    if df.empty:
        return None

    df = calculate_vwap(df)

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

        risk_pct = risk / entry
        if not (0.003 <= risk_pct <= 0.012):
            continue

        target = round(entry + risk * 2, 2)

        # RESULT CHECK
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
            "time": r.name,
            "entry": entry,
            "sl": sl,
            "target": target,
            "result": result,
            "score": f"{score}/5"
        }

    return None

# ================= SCAN (CORE FIX) =================

def scan_stock(symbol, date=None):
    df15, df5 = get_data(symbol)
    if df15 is None:
        return None

    df15 = df15.between_time("09:45", "13:30")

    radars = find_radars(df15)

    used_days = set()

    for radar_time in radars:
        if date and radar_time.date() != pd.to_datetime(date).date():
            continue

        day = radar_time.date()

        # ONLY FIRST TRADE PER DAY
        if day in used_days:
            continue

        trade = find_trade(
            df5[df5.index.date == day],
            radar_time
        )

        if trade:
            used_days.add(day)
            return {
                "symbol": symbol,
                "radar": radar_time,
                "trade": trade
            }

    return None

# ================= FORMAT =================

def format_result(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar'].strftime('%Y-%m-%d %H:%M')}\n"

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

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "").upper()

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, "📅 SCANNING...")

        for s in FNO_STOCKS:
            r = scan_stock(s, text)
            if r:
                send(chat_id, format_result(r))

        return "ok"

    # SINGLE STOCK
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        r = scan_stock(sym + ".NS", d)

        if r:
            send(chat_id, format_result(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()

        for d in pd.date_range(d1, d2):
            r = scan_stock(sym + ".NS", str(d.date()))
            if r:
                send(chat_id, format_result(r))

        return "ok"

    # RADAR
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]

        for s in FNO_STOCKS:
            df15, _ = get_data(s)
            if df15 is None:
                continue

            radars = find_radars(df15)

            for r in radars:
                if r.date() == pd.to_datetime(d).date():
                    send(chat_id, f"{s} → {r.strftime('%H:%M')}")

        return "ok"

    send(chat_id, "Command OK")
    return "ok"

@app.route("/")
def home():
    return "BOT RUNNING"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
