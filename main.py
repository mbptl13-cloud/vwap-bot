import os
import re
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from flask import Flask, request

# ================= CONFIG =================

BOT_TOKEN = "8695080537:AAFolODguF8s1z88s_57HTVModIrmGojlno"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

FNO_STOCKS = ["ADANIGREEN.NS", "BHEL.NS", "RELIANCE.NS", "TCS.NS"]

# ================= CONTROL =================

RUNNING = {}
STOP_FLAG = {}
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
    if key in LAST_REQUEST and now - LAST_REQUEST[key] < 10:
        return True
    LAST_REQUEST[key] = now
    return False

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

# ================= VWAP =================

def add_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    df["TPV"] = tp * df["Volume"]

    df["CUM_TPV"] = df.groupby(df.index.date)["TPV"].cumsum()
    df["CUM_VOL"] = df.groupby(df.index.date)["Volume"].cumsum()

    df["VWAP"] = df["CUM_TPV"] / df["CUM_VOL"]
    return df

# ================= 15M =================

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

        if (
            r["Volume"] > 500000 and
            (r["Close"] * r["Volume"]) > 150000000 and
            ((r["High"] - r["Low"]) / r["Open"]) * 100 > 1 and
            (abs(r["Close"] - r["Open"]) / r["Open"]) * 100 > 0.6 and
            r["Close"] > r["VWAP"] and
            r["Volume"] > 2 * r["VOL_SMA20"] and
            r["Close"] > r["Open"]
        ):
            radars.append(r.name + pd.Timedelta(minutes=15))

    return radars

# ================= 5M =================

def find_5m(df, radar_time):
    df = add_vwap(df.copy())
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

        target = round(entry + risk * 2, 2)

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
            "result": result
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

# ================= FORMAT =================

def fmt(r):
    if r is None:
        return "No data"

    if isinstance(r["radar"], str):
        return f"{r['symbol']} → {r['radar']}"

    msg = f"📊 {r['symbol']}\n15M: {r['radar']}\n"

    if r["trade"]:
        t = r["trade"]
        msg += f"5M: {t['time']}\nEntry: {t['entry']} SL: {t['sl']} TG: {t['target']}\nResult: {t['result']}"
    else:
        msg += "5M: NO SETUP"

    return msg

# ================= THREAD WORKERS =================

def range_worker(chat_id, sym, d1, d2):
    STOP_FLAG[chat_id] = False
    send(chat_id, f"📊 RANGE {sym}")

    for i, d in enumerate(pd.date_range(d1, d2)):

        if STOP_FLAG.get(chat_id):
            send(chat_id, "🛑 Scan stopped")
            return

        if i > 20:
            send(chat_id, "⚠️ Limit reached")
            return

        r = scan_stock(sym + ".NS", str(d.date()))
        send(chat_id, fmt(r))

        time.sleep(0.3)

# ================= WEBHOOK =================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "").strip().upper()

    if is_duplicate(chat_id, text):
        return "ok"

    # STOP
    if text == "STOP":
        STOP_FLAG[chat_id] = True
        send(chat_id, "🛑 Stopping...")
        return "ok"

    # START
    if text == "/START":
        send(chat_id,
"""🤖 FNO BACKTEST BOT

Commands:
DATE → 2026-04-27
STOCK → BHEL 2026-04-27
RANGE → ADANIGREEN 2026-04-01 TO 2026-04-10
RADAR → 2026-04-27 RADAR

Send STOP anytime to cancel
""")
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

    # RANGE (THREAD)
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}", text):
        sym, d1, _, d2 = text.split()

        STOP_FLAG[chat_id] = True  # stop previous

        t = threading.Thread(target=range_worker, args=(chat_id, sym, d1, d2))
        t.start()

        return "ok"

    # STOCK DATE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, d = text.split()
        send(chat_id, fmt(scan_stock(sym + ".NS", d)))
        return "ok"

    # DATE
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, f"📅 SCANNING {text}")
        for s in FNO_STOCKS:
            send(chat_id, fmt(scan_stock(s, text)))
        return "ok"

    send(chat_id, "❌ Invalid command")
    return "ok"

# ================= RUN =================

@app.route("/")
def home():
    return "RUNNING"

if __name__ == "__main__":
    requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)
