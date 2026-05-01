import os
import re
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request
from datetime import datetime

# ================= CONFIG =================
BOT_TOKEN = "8218143624:AAGr75U7tVRiXKES5WIJneD6MotImx66qis"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

FNO_STOCKS = ["ADANIGREEN.NS", "BHEL.NS", "RELIANCE.NS", "TCS.NS"]

# ================= TELEGRAM =================
def send(chat_id, text):
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20
        )
    except:
        pass

# ================= DATA =================
def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="30d", progress=False)

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


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


def session_filter(df):
    return df.between_time("09:45", "15:30")


def filter_date(df, date):
    d = pd.to_datetime(date).date()
    df = df[df.index.date == d]
    return df if not df.empty else None


# ================= VWAP (CORRECT) =================
def vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


# ================= 15M RADAR =================
def find_radar(df):
    df = df.copy()
    df["VWAP"] = vwap(df)
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(20, len(df)):
        r = df.iloc[i]
        t = r.name.time()

        # ✅ STRICT RADAR WINDOW
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA"]):
            continue

        body = abs(r["Close"] - r["Open"]) / r["Open"]

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > 500000
            and r["Volume"] > 2 * r["VOL_SMA"]
            and body > 0.006
        ):
            radars.append(r.name)   # 🔥 NO SHIFT

    return radars


# ================= 5M TRADE =================
def find_trade(df5, radar_time):

    # 🔥 SAME DAY ONLY
    df = df5[df5.index.date == radar_time.date()]
    df = df[df.index > radar_time].copy()

    if df.empty:
        return None

    df = df.copy()
    df["VWAP"] = vwap(df)

    for i in range(1, len(df)):

        row = df.iloc[i]
        prev = df.iloc[i - 1]

        # 🔥 STRICT NO SAME CANDLE ENTRY
        if row.name <= radar_time:
            continue

        t = row.name.time()

        # ENTRY WINDOW
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        # ================= SCORE =================
        score = 0

        if row["Low"] <= row["VWAP"] * 1.002 and row["Close"] > row["VWAP"]:
            score += 1

        if row["Close"] > row["VWAP"]:
            score += 1

        if row["Close"] > prev["High"]:
            score += 1

        if row["Volume"] > prev["Volume"] * 1.2:
            score += 1

        if score < 4:
            continue

        # ================= TRADE =================
        entry = float(row["High"])
        sl = float(prev["VWAP"])

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk / entry <= 0.012):
            continue

        target = entry + (risk * 2)

        # ================= RESULT =================
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
            "time": row.name,
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "target": round(target, 2),
            "result": result,
            "score": f"{score}/5"
        }

    return None


# ================= BACKTEST =================
def scan_stock(symbol, date):

    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return None

    df15 = session_filter(df15)
    df15 = filter_date(df15, date)

    if df15 is None:
        return None

    radars = find_radar(df15)

    if not radars:
        return None

    for r in radars:
        trade = find_trade(df5, r)

        return {
            "symbol": symbol,
            "radar": r,
            "trade": trade
        }

    return None


def scan_all(date):
    results = []

    for s in FNO_STOCKS:
        r = scan_stock(s, date)
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

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "").strip().upper()

    # DATE BACKTEST
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):

        send(chat_id, f"📅 SCANNING {text}")

        results = scan_all(text)

        if not results:
            send(chat_id, "No setup")
            return "ok"

        for r in results:
            send(chat_id, fmt(r))

        return "ok"

    send(chat_id, "Command OK")
    return "ok"


@app.route("/")
def home():
    return "BACKTEST BOT RUNNING"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
