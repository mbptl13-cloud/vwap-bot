import os
import re
import time
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request
from datetime import datetime

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
RENDER_URL = "https://your-url.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ================= CONFIG =================

DATE_DELAY = 1   # delay for bulk scan (avoid timeout)

FNO_STOCKS = [
    "ADANIGREEN.NS","BHEL.NS","RELIANCE.NS","TCS.NS","TATAPOWER.NS"
]

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

    return df[["Open","High","Low","Close","Volume"]].dropna()


def to_ist(df):
    if df is None: return None
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
        df = df.between_time("09:15","15:30")
        return df if not df.empty else None
    except:
        return None


def filter_date(df, date):
    d = pd.to_datetime(date).date()
    df = df[df.index.date == d]
    return df if not df.empty else None


# ================= VWAP FIX =================

def calculate_vwap_intraday(df):
    df = df.copy()

    df["DATE"] = df.index.date
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3

    df["CUM_VOL"] = df.groupby("DATE")["Volume"].cumsum()
    df["CUM_TPV"] = (df["TP"] * df["Volume"]).groupby(df["DATE"]).cumsum()

    df["VWAP"] = df["CUM_TPV"] / df["CUM_VOL"]

    return df["VWAP"]


# ================= 15M RADAR =================

def find_15m(df):
    df = df.copy()
    df["VWAP"] = calculate_vwap_intraday(df)
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    out = []

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
            out.append({
                "time": df.index[i] + pd.Timedelta(minutes=15)
            })

    return out


# ================= 5M TRADE =================

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

        # SCORE
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

        # ENTRY
        entry = round(r["High"], 2)
        sl = round(p["VWAP"], 2)

        risk = entry - sl
        if risk <= 0:
            continue

        risk_pct = risk / entry

        # STRICT FILTER (THIS FIXES YOUR ISSUE)
        if not (0.003 <= risk_pct <= 0.012):
            continue

        target = round(entry + (risk * 2), 2)

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
            "time": df.index[i] + pd.Timedelta(minutes=5),
            "entry": entry,
            "sl": sl,
            "target": target,
            "result": result,
            "score": f"{score}/5"
        }

    return None


# ================= SCAN =================

def scan_stock(sym, date):
    df15 = to_ist(get_data(sym, "15m"))
    df5 = to_ist(get_data(sym, "5m"))

    if df15 is None:
        return None

    df15 = filter_date(df15, date)
    df15 = session_filter(df15)

    if df15 is None:
        return None

    radars = find_15m(df15)

    if not radars:
        return None

    for r in radars:
        trade = None

        if df5 is not None:
            df5d = filter_date(df5, date)

            if df5d is not None:
                trade = find_5m(df5d, r["time"])

        # FIRST VALID TRADE ONLY
        if trade:
            return {"symbol": sym, "radar": r, "trade": trade}

    return None


def scan_all(date):
    out = []
    for s in FNO_STOCKS:
        r = scan_stock(s, date)
        if r:
            out.append(r)
        time.sleep(DATE_DELAY)
    return out


def run_range(sym, d1, d2):
    out = []

    for d in pd.date_range(d1, d2):
        r = scan_stock(sym, str(d.date()))
        if r:
            out.append(r)

    return out


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


# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    # DATE SCAN
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, f"📅 SCANNING {text}")

        results = scan_all(text)

        if not results:
            send(chat_id, "No setups found")
            return "ok"

        for r in results:
            send(chat_id, fmt(r))

        return "ok"

    # SINGLE STOCK
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        r = scan_stock(sym + ".NS", d)

        if r:
            send(chat_id, fmt(r))
        else:
            send(chat_id, "No setup")

        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()

        results = run_range(sym + ".NS", d1, d2)

        for r in results:
            send(chat_id, fmt(r))

        return "ok"

    # RADAR ONLY
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]

        for s in FNO_STOCKS:
            r = scan_stock(s, d)
            if r:
                send(chat_id, f"{s} → {r['radar']['time'].strftime('%H:%M')}")

        return "ok"

    send(chat_id, "Command OK")
    return "ok"


@app.route("/")
def home():
    return "BOT RUNNING"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
