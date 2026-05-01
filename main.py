import os
import re
import time
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request
from datetime import datetime

# ================= CONFIG =================
BOT_TOKEN = "8218143624:AAGr75U7tVRiXKES5WIJneD6MotImx66qis"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
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

    return df[["Open","High","Low","Close","Volume"]].dropna()


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


def filter_date(df, d):
    d = pd.to_datetime(d).date()
    df = df[df.index.date == d]
    return df if not df.empty else None


# ================= FIXED VWAP (SESSION RESET) =================
def vwap_session(df):
    df = df.copy()

    df["date"] = df.index.date
    tp = (df["High"] + df["Low"] + df["Close"]) / 3

    vwap_list = []

    for d, g in df.groupby("date"):
        cum_vol = g["Volume"].cumsum()
        vwap = (tp[g.index] * g["Volume"]).cumsum() / cum_vol
        vwap_list.append(vwap)

    df["VWAP"] = pd.concat(vwap_list).sort_index()
    return df


# ================= 15M RADAR =================
def find_radar(df):
    df = vwap_session(df)
    df["VOL_SMA"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(20, len(df)):
        r = df.iloc[i]

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA"]):
            continue

        body = abs(r["Close"] - r["Open"]) / r["Open"]

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > 500000
            and r["Volume"] > 2 * r["VOL_SMA"]
            and body > 0.006
        ):
            radars.append(df.index[i])

    return radars


# ================= 5M TRADE =================
def find_trade(df5, radar_time):
    df = df5[df5.index > radar_time].copy()
    if df.empty:
        return None

    df = vwap_session(df)

    entry_found = False

    for i in range(1, len(df)):
        r = df.iloc[i]
        p = df.iloc[i-1]

        t = r.name.time()

        # ENTRY WINDOW FIX
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        score = 0

        if r["Low"] <= r["VWAP"] * 1.002 and r["Close"] > r["VWAP"]:
            score += 1
        if r["Close"] > r["VWAP"]:
            score += 1
        if r["Close"] > p["High"]:
            score += 1
        if r["Volume"] > p["Volume"] * 1.2:
            score += 1

        if score < 4:
            continue

        entry = float(r["High"])
        sl = float(p["VWAP"])
        risk = entry - sl

        if risk <= 0:
            continue

        if not (0.003 <= risk / entry <= 0.012):
            continue

        target = entry + (risk * 2)

        # ================= RESULT FIX =================
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
            "entry": round(entry,2),
            "sl": round(sl,2),
            "target": round(target,2),
            "result": result,
            "score": f"{score}/5"
        }

    return None


# ================= BACKTEST ENGINE =================
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

    # ✅ FIRST TRADE ONLY
    for r in radars:
        trade = find_trade(df5, r)

        return {
            "symbol": symbol,
            "radar": r,
            "trade": trade
        }

    return None


def scan_all(date):
    res = []
    for s in FNO_STOCKS:
        r = scan_stock(s, date)
        if r:
            res.append(r)
    return res


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
    text = data["message"].get("text","").strip().upper()

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

    # RANGE BACKTEST
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()

        send(chat_id, f"📊 RANGE {sym}")

        for d in pd.date_range(d1, d2):
            r = scan_stock(sym+".NS", str(d.date()))
            if r:
                send(chat_id, fmt(r))

        return "ok"

    send(chat_id, "Command OK")
    return "ok"


@app.route("/")
def home():
    return "BACKTEST BOT RUNNING"


if __name__ == "__main__":
    print("BACKTEST BOT STARTED")
    app.run(host="0.0.0.0", port=PORT)
