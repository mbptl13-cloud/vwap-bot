import os
import re
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request

# =====================================
# CONFIG
# =====================================

BOT_TOKEN = "8695080537:AAFolODguF8s1z88s_57HTVModIrmGojlno"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# =====================================
# TELEGRAM DEDUP (FIXED)
# =====================================

PROCESSED_UPDATES = set()

def is_duplicate(update_id):
    if update_id in PROCESSED_UPDATES:
        return True

    PROCESSED_UPDATES.add(update_id)

    if len(PROCESSED_UPDATES) > 1000:
        PROCESSED_UPDATES.clear()

    return False

# =====================================
# SEND MESSAGE
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
# DATA FETCH
# =====================================

def get_data(symbol, interval):
    try:
        df = yf.download(symbol, interval=interval, period="30d", progress=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

        df.index = pd.to_datetime(df.index)

        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")

        df.index = df.index.tz_convert("Asia/Kolkata")

        df = df.between_time("09:15", "15:30")

        return df if not df.empty else None

    except Exception as e:
        print("Download Error:", e)
        return None

# =====================================
# DATE FILTER (FIXED)
# =====================================

def filter_date(df, date_str):
    if df is None:
        return None

    df = df.copy()
    d = pd.to_datetime(date_str).date()

    df["temp_date"] = df.index.date
    df = df[df["temp_date"] == d]
    df = df.drop(columns=["temp_date"])

    return df if not df.empty else None

# =====================================
# VWAP (TRADINGVIEW STYLE SAFE)
# =====================================

def calculate_vwap(df):
    df = df.copy()

    tp = (df["High"] + df["Low"] + df["Close"]) / 3

    cum_vol = df["Volume"].groupby(df.index.date).cumsum()
    cum_pv = (tp * df["Volume"]).groupby(df.index.date).cumsum()

    vwap = cum_pv / cum_vol

    return vwap.astype(float)   # 🔥 FORCE SCALAR SERIES
# =====================================
# 15M RADAR (STRICT LOGIC)
# =====================================

def find_15m_radars(df):
    if df is None or len(df) < 20:
        return []

    df = df.copy()
    df["VWAP"] = calculate_vwap(df).values
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(19, len(df)):

        if df.index[i].time() < pd.to_datetime("09:45").time():
            continue

        row = df.iloc[i]

        vwap_val = row["VWAP"]

        if isinstance(vwap_val, pd.Series):
            vwap_val = vwap_val.iloc[0]

        vwap_val = float(vwap_val)
        vol_val = row["VOL_SMA20"]

        if isinstance(vol_val, pd.Series):
            vol_val = vol_val.iloc[0]

        vol_val = float(vol_val) 
        if not pd.isna(vol_val) 
        else 0
        if pd.isna(vwap_val) or pd.isna(vol_val):
            continue

        body = abs(row["Close"] - row["Open"]) / row["Open"]
        rng = (row["High"] - row["Low"]) / row["Open"]

        if (
            row["Close"] > vwap_val
            and row["Volume"] > 500000
            and row["Volume"] > 2 * vol_val
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

        t = row.name.time()

        if not (pd.to_datetime("09:45").time() <= t <= pd.to_datetime("13:30").time()):
            continue

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

        entry = round(row["High"], 2)
        sl = round(prev["VWAP"], 2)

        risk = entry - sl
        if risk <= 0:
            continue

        if not (0.003 <= risk / entry <= 0.015):
            continue

        target = round(entry + (risk * 2), 2)

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
            "score": f"{score}/5"
        }

    return None

# =====================================
# SCAN ENGINE
# =====================================

def scan_stock(symbol, date):
    df15 = get_data(symbol, "15m")
    df5 = get_data(symbol, "5m")

    df15 = filter_date(df15, date)
    df5 = filter_date(df5, date)

    if df15 is None:
        return None

    radars = find_15m_radars(df15)

    if not radars:
        return None

    for r in radars:
        trade = find_5m_trade(df5, r["time"])
        return {"symbol": symbol, "radar": r, "trade": trade}

    return None

# =====================================
# FORMAT OUTPUT
# =====================================

def format_result(r):
    msg = f"📊 {r['symbol']}\n"
    msg += f"15M: {r['radar']['time']}\n"

    if r["trade"]:
        t = r["trade"]
        msg += f"5M: {t['time']}\n"
        msg += f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
        msg += f"Result: {t['result']}"
    else:
        msg += "⚡ RADAR ONLY"

    return msg

# =====================================
# WEBHOOK
# =====================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    update_id = data.get("update_id")

    if update_id and is_duplicate(update_id):
        return "ok"

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip().upper()

    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, date = text.split()
        symbol = sym + ".NS"

        send(chat_id, f"🔍 {sym} {date}")

        result = scan_stock(symbol, date)

        if not result:
            send(chat_id, "❌ No setup found")
            return "ok"

        send(chat_id, format_result(result))
        return "ok"

    send(chat_id, "Command OK")
    return "ok"

# =====================================
# RUN
# =====================================

@app.route("/")
def home():
    return "BOT RUNNING"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
