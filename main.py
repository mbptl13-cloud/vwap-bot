import os
import re
import time
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request

# ================= CONFIG =================

BOT_TOKEN = "8218143624:AAGr75U7tVRiXKES5WIJneD6MotImx66qis"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
LAST_REQUEST = {}

# ================= TELEGRAM =================

def send(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage",
                      json={"chat_id": chat_id, "text": text},
                      timeout=20)
    except:
        pass


def is_duplicate(chat_id, text):
    key = f"{chat_id}:{text}"
    now = time.time()
    if key in LAST_REQUEST and now - LAST_REQUEST[key] < 3:
        return True
    LAST_REQUEST[key] = now
    return False


def set_webhook():
    try:
        requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    except:
        pass

# ================= STOCKS =================

FNO_STOCKS = ["ADANIGREEN.NS", "BHEL.NS", "RELIANCE.NS", "TCS.NS"]

# ================= DATA =================

def get_data(symbol, interval):
    try:
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

    except:
        return None


def filter_date(df, d):
    d = pd.to_datetime(d).date()
    df = df[df.index.date == d]
    return df if not df.empty else None

# ================= VWAP =================

def vwap(df):
    df = df.copy()

    tp = (df["High"] + df["Low"] + df["Close"]) / 3

    df["TPV"] = tp * df["Volume"]

    # GROUP BY DATE → RESET DAILY
    df["CUM_TPV"] = df.groupby(df.index.date)["TPV"].cumsum()
    df["CUM_VOL"] = df.groupby(df.index.date)["Volume"].cumsum()

    df["VWAP"] = df["CUM_TPV"] / df["CUM_VOL"]

    return df["VWAP"]

# ================= 15M RADAR =================

def find_15m(df):
    df = df.copy()

    df["VWAP"] = vwap(df)
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(20, len(df)):
        r = df.iloc[i]

        # Time filter
        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA20"]):
            continue

        # CONDITIONS (EXACT MATCH)
        volume_cond = r["Volume"] > 500000
        turnover_cond = (r["Close"] * r["Volume"]) > 150000000

        range_pct = ((r["High"] - r["Low"]) / r["Open"]) * 100
        range_cond = range_pct > 1

        body_pct = (abs(r["Close"] - r["Open"]) / r["Open"]) * 100
        body_cond = body_pct > 0.6

        vwap_cond = r["Close"] > r["VWAP"]
        vol_spike_cond = r["Volume"] > (2 * r["VOL_SMA20"])
        bullish_cond = r["Close"] > r["Open"]

        if (
            volume_cond and
            turnover_cond and
            range_cond and
            body_cond and
            vwap_cond and
            vol_spike_cond and
            bullish_cond
        ):
            radars.append(df.index[i] + pd.Timedelta(minutes=15))

    return radars

# ================= 5M TRADE =================

def find_5m(df, radar_time):
    if df is None:
        return None

    df = df.copy()

    # FULL VWAP first
    df["VWAP"] = vwap(df)

    # After radar
    df = df[df.index > radar_time]

    if df.empty:
        return None

    for i in range(1, len(df)):
        r = df.iloc[i]
        p = df.iloc[i - 1]

        t = r.name.time()
        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("15:30").time()):
            continue

        score = 0

        if r["Low"] <= r["VWAP"] * 1.003:
            score += 1
        if r["Close"] > p["High"]:
            score += 1
        if r["Close"] > r["Open"]:
            score += 1
        if r["Volume"] > p["Volume"] * 1.1:
            score += 1

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

        if not (0.003 <= risk / entry <= 0.02):
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
            "time": df.index[i],
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

    df15 = filter_date(df15, date)
    if df15 is None:
        return None

    radars = find_15m(df15)

    if not radars:
        return {
            "symbol": sym,
            "radar": f"{date} → NO RADAR",
            "trade": None
        }

    radar = radars[0]

    trade = None

    if df5 is not None:
        df5 = filter_date(df5, date)
        if df5 is not None:
            trade = find_5m(df5, radar)

    return {
        "symbol": sym,
        "radar": radar,
        "trade": trade
    }

# ================= RANGE =================

def run_range(sym, d1, d2):
    res = []
    for d in pd.date_range(d1, d2):
        r = scan_stock(sym, str(d.date()))
        if r:
            res.append(r)
    return res

# ================= FORMAT =================

def fmt(r):
    if isinstance(r["radar"], str):
        return f"{r['symbol']} → {r['radar']}"

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

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    if is_duplicate(chat_id, text):
        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()
        send(chat_id, f"📊 RANGE {sym}")

        for r in run_range(sym + ".NS", d1, d2):
            send(chat_id, fmt(r))

        return "ok"

    # SYMBOL DATE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        r = scan_stock(sym + ".NS", d)
        send(chat_id, fmt(r))
        return "ok"

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, f"📅 SCANNING {text}")

        for s in FNO_STOCKS:
            r = scan_stock(s, text)
            if r:
                send(chat_id, fmt(r))

        return "ok"

    # DATE RADAR
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        d = text.split()[0]
        send(chat_id, f"📡 RADAR {d}")

        for s in FNO_STOCKS:
            r = scan_stock(s, d)
            if r and not isinstance(r["radar"], str):
                send(chat_id, f"{s} → {r['radar']}")

        return "ok"

    send(chat_id, "Command OK")
    return "ok"

# ================= RUN =================

@app.route("/")
def home():
    return "BACKTEST BOT RUNNING"

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=PORT)
