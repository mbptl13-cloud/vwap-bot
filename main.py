import os
import re
import time
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request
from datetime import datetime

BOT_TOKEN = "8695080537:AAFolODguF8s1z88s_57HTVModIrmGojlno"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

LAST_REQUEST = {}

def is_duplicate(chat_id, text):
    key = f"{chat_id}:{text}"
    now = time.time()

    if key in LAST_REQUEST and now - LAST_REQUEST[key] < 5:
        return True

    LAST_REQUEST[key] = now
    return False


# ================= DATA =================

def get_data(symbol, interval):
    try:
        df = yf.download(symbol, interval=interval, period="30d", progress=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df if not df.empty else None

    except:
        return None


def to_ist(df):
    if df is None:
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


def filter_date(df, date):
    d = pd.to_datetime(date).date()
    return df[df.index.date == d]


def calculate_vwap(df):
    df = df.copy()
    tp = (df["High"] + df["Low"] + df["Close"]) / 3

    df["VWAP"] = (
        (tp * df["Volume"]).groupby(df.index.date).cumsum()
        /
        df["Volume"].groupby(df.index.date).cumsum()
    )

    return df["VWAP"]


# ================= STRATEGY =================

def find_15m_radars(df):
    if df is None or len(df) < 20:
        return []

    df = df.copy()
    df["VWAP"] = calculate_vwap(df)
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(19, len(df)):

        # ✅ 👉 PASTE IT HERE
        if df.index[i].time() < pd.to_datetime("09:45").time():
            continue

        row = df.iloc[i]

        if pd.isna(row["VWAP"]) or pd.isna(row["VOL_SMA20"]):
            continue

        body = abs(row["Close"] - row["Open"]) / row["Open"]
        rng = (row["High"] - row["Low"]) / row["Open"]

        if (
            
            row["Volume"] > 500000
            and row["Volume"] > 2 * row["VOL_SMA20"]
            and body > 0.006
            and rng > 0.006
            and row["Close"] > row["Open"]
        ):
            radars.append({
                "time": df.index[i] + pd.Timedelta(minutes=15)
            })

    return radars


def find_5m_trade(df, radar_time):
    df = df[df.index > radar_time].copy()
    if df.empty:
        return None

    df["VWAP"] = calculate_vwap(df)

    for i in range(1, len(df)):
        r = df.iloc[i]
        prev = df.iloc[i - 1]

        score = 0

        if r["Close"] > r["VWAP"]:
            score += 1
        if r["Close"] > prev["High"]:
            score += 1
        if r["Volume"] > prev["Volume"]:
            score += 1
        if r["Low"] <= r["VWAP"]:
            score += 1

        if score < 3:
            continue

        entry = round(r["High"], 2)
        sl = round(prev["VWAP"], 2)
        target = round(entry + (entry - sl) * 2, 2)

        result = "OPEN"

        for j in range(i + 1, len(df)):
            nxt = df.iloc[j]

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
            "score": score
        }

    return None

def session_filter_full(df):
    if df is None:
        return None

    try:
        df = df.between_time("09:15", "15:30")
        return df if not df.empty else None
    except:
        return None


def scan_stock(symbol, date):
    df15 = get_data(symbol, "15m")
    df15 = to_ist(df15)
    df15 = session_filter_full(df15)

    if df15 is None:
        return None

    df15["VWAP"] = calculate_vwap(df15)

    df5 = get_data(symbol, "5m")
    df5 = to_ist(df5)
    df5 = session_filter_full(df5)

    if df5 is not None:
        df5["VWAP"] = calculate_vwap(df5)

    df15 = filter_date(df15, date)
    if df15 is None:
        return None

    radars = find_15m_radars(df15)

    if not radars:
        return None

    for r in radars:
        trade = None

        if df5 is not None:
            temp5 = filter_date(df5, date)
            if temp5 is not None:
                trade = find_5m_trade(temp5, r["time"])

        # ✅ ALWAYS return radar (even if trade None)
        return {
            "symbol": symbol,
            "radar": r,
            "trade": trade
        }

    return None


# ================= FORMAT =================

def format_result(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']['time']}\n"

    if r["trade"]:
        t = r["trade"]
        msg += f"5M: {t['time']}\n"
        msg += f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
        msg += f"Result: {t['result']}"
    else:
        msg += "⚡ RADAR ONLY (No 5M setup)"

    return msg


# ================= TELEGRAM =================

def send(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})
    except:
        pass


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

    try:

        # STOCK DATE
        if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
            sym, date = text.split()
            symbol = sym + ".NS"

            send(chat_id, f"🔍 {sym} {date}")

            res = scan_stock(symbol, date)

            if res:
                send(chat_id, format_result(res))
            else:
                send(chat_id, "❌ No setup found")

            return "ok"

        # DATE SCAN ALL
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            send(chat_id, "📊 SCANNING ALL STOCKS...")

            found = False

            for s in FNO_STOCKS:
                res = scan_stock(s, text)
                if res:
                    send(chat_id, format_result(res))
                    found = True

            if not found:
                send(chat_id, "❌ No setups")

            return "ok"

        send(chat_id, "❌ Invalid Command")

    except Exception as e:
        send(chat_id, f"ERROR: {str(e)}")

    return "ok"


@app.route("/")
def home():
    return "BOT RUNNING"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
