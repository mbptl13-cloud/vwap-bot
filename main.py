import os
import re
import time
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request
from datetime import datetime

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = "8695080537:AAFolODguF8s1z88s_57HTVModIrmGojlno"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# =====================================
# ANTI DUPLICATE
# =====================================

LAST_REQUEST = {}

def is_duplicate(chat_id, text):
    key = f"{chat_id}:{text}"
    now = time.time()

    if key in LAST_REQUEST:
        if now - LAST_REQUEST[key] < 5:
            return True

    LAST_REQUEST[key] = now
    return False


# =====================================
# STOCK LIST
# =====================================

FNO_STOCKS = [
    "ADANIGREEN.NS",
    "BHEL.NS",
    "RELIANCE.NS",
    "TCS.NS"
]


# =====================================
# TELEGRAM SEND
# =====================================

def send(chat_id, text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20
        )
    except Exception as e:
        print("Send Error:", e)


# =====================================
# WEBHOOK
# =====================================

def set_webhook():
    try:
        url = f"{RENDER_URL}/webhook"
        requests.get(f"{BASE_URL}/setWebhook?url={url}", timeout=20)
        print("Webhook set:", url)
    except Exception as e:
        print("Webhook Error:", e)


# =====================================
# DATA
# =====================================

def get_data(symbol, interval):
    try:
        df = yf.download(symbol, interval=interval, period="30d", progress=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df"Open", "High", "Low", "Close", "Volume".dropna()
        return df if not df.empty else None

    except Exception as e:
        print("Download Error:", symbol, e)
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
    except Exception:
        pass

    return df


def session_filter(df):
    if df is None:
        return None
    try:
        df = df.between_time("09:45", "13:30")
        return df if not df.empty else None
    except:
        return None


def filter_date(df, date_str):
    if df is None:
        return None

    d = pd.to_datetime(date_str).date()
    df = df[df.index.date == d]

    return df if not df.empty else None


def calculate_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


# =====================================
# 15M RADAR
# =====================================

def find_15m_radars(df):
    if df is None or len(df) < 20:
        return []

    df = df.copy()
    df["VWAP"] = calculate_vwap(df)
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(19, len(df)):
        row = df.iloc[i]

        if pd.isna(row["VWAP"]) or pd.isna(row["VOL_SMA20"]):
            continue

        body = abs(row["Close"] - row["Open"]) / row["Open"]
        rng = (row["High"] - row["Low"]) / row["Open"]

        if (
            row["Close"] > row["VWAP"]
            and row["Volume"] > 500000
            and row["Volume"] > 2 * row["VOL_SMA20"]
            and body > 0.006
            and rng > 0.006
            and row["Close"] > row["Open"]
        ):
            radars.append({
                "time": df.index[i] + pd.Timedelta(minutes=15)
            })

    return radars


# =====================================
# 5M TRADE
# =====================================

def find_5m_trade(df5, radar_time):
    if df5 is None:
        return None

    df = df5[df5.index > radar_time].copy()
    if df.empty:
        return None

    df["VWAP"] = calculate_vwap(df)

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if pd.isna(prev["VWAP"]):
            continue

        # Entry window
        t = row.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        # Score
        score = 0

        if row["Low"] <= row["VWAP"] * 1.002 and row["Close"] > row["VWAP"]:
            score += 1

        if (row["Close"] - row["Low"]) > ((row["High"] - row["Low"]) * 0.5):
            score += 1

        if row["Close"] > row["VWAP"]:
            score += 1

        if row["Close"] > prev["High"] and row["Close"] > row["Open"]:
            score += 1

        if row["Volume"] > prev["Volume"] * 1.2:
            score += 1

        if score < 4:
            continue

        # ENTRY / SL / TARGET
        entry = round(row["High"], 2)
        sl = round(prev["VWAP"], 2)

        risk = entry - sl
        if risk <= 0:
            continue

        risk_pct = risk / entry
        if not (0.003 <= risk_pct <= 0.015):
            continue

        target = round(entry + (risk * 2), 2)

        # RESULT till 15:30
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


# =====================================
# SCAN
# =====================================

def scan_stock(symbol, date=None):
    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return None

    df15 = session_filter(df15)
    if df15 is None:
        return None

    radars = find_15m_radars(df15)
    if not radars:
        return None

    for r in radars:
        if date and r["time"].date() != pd.to_datetime(date).date():
            continue

        trade = None
        if df5 is not None:
            temp5 = filter_date(df5, r["time"].strftime("%Y-%m-%d"))
            if temp5 is not None:
                trade = find_5m_trade(temp5, r["time"])

        return {"symbol": symbol, "radar": r, "trade": trade}

    return None


def run_range(symbol, d1, d2):
    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return []

    df15 = session_filter(df15)
    if df15 is None:
        return []

    radars = find_15m_radars(df15)

    results = []

    for r in radars:
        d = r["time"].date()
        if not (pd.to_datetime(d1).date() <= d <= pd.to_datetime(d2).date()):
            continue

        trade = None
        if df5 is not None:
            temp5 = filter_date(df5, r["time"].strftime("%Y-%m-%d"))
            if temp5 is not None:
                trade = find_5m_trade(temp5, r["time"])

        results.append({"symbol": symbol, "radar": r, "trade": trade})

    return results


# =====================================
# FORMAT
# =====================================

def format_result(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']['time']}\n"

    if r["trade"]:
        t = r["trade"]
        msg += f"5M: {t['time']}\n"
        msg += f"Score: {t['score']}\n"
        msg += f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
        msg += f"Result: {t['result']}"
    else:
        msg += "5M: NO SETUP"

    return msg


# =====================================
# WEBHOOK
# =====================================

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

    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()
        symbol = sym + ".NS"

        send(chat_id, f"📊 RANGE SCANNING {sym}")

        results = run_range(symbol, d1, d2)

        if not results:
            send(chat_id, "No setups in range")
            return "ok"

        for r in results:
            if r["trade"]:
                send(chat_id, format_result(r))
            else:
                send(chat_id, f"{r['symbol']} → {r['radar']['time']} → NO 5M SETUP")

        return "ok"

    send(chat_id, "Command OK")
    return "ok"


@app.route("/")
def home():
    return "BOT RUNNING"


if __name__ == "__main__":
    print("🚀 BOT STARTING")
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)
