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

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
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
            json={
                "chat_id": chat_id,
                "text": text
            },
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

        requests.get(
            f"{BASE_URL}/setWebhook?url={url}",
            timeout=20
        )

        print("Webhook set:", url)

    except Exception as e:
        print("Webhook Error:", e)


# =====================================
# DATA
# =====================================

def get_data(symbol, interval):
    try:
        df = yf.download(
            symbol,
            interval=interval,
            period="30d",
            progress=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        needed = ["Open", "High", "Low", "Close", "Volume"]

        for col in needed:
            if col not in df.columns:
                return None

        df = df[needed].copy()
        df.dropna(inplace=True)

        if df.empty:
            return None

        return df

    except Exception as e:
        print("Download Error:", symbol, e)
        return None


def to_ist(df):
    if df is None or df.empty:
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
    if df is None or df.empty:
        return None

    try:
        df = df.between_time("09:45", "13:30")
    except Exception:
        return None

    if df.empty:
        return None

    return df


def filter_date(df, date_str):
    if df is None or df.empty:
        return None

    target = pd.to_datetime(date_str).date()

    df = df.copy()
    df["only_date"] = df.index.date
    df = df[df["only_date"] == target]
    df.drop(columns=["only_date"], inplace=True)

    if df.empty:
        return None

    return df


def calculate_vwap(df):
    if df is None or df.empty:
        return None

    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    vol_sum = df["Volume"].cumsum()

    if (vol_sum == 0).any():
        return None

    return (tp * df["Volume"]).cumsum() / vol_sum


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

        open_price = float(row["Open"])

        if open_price <= 0:
            continue

        body_pct = abs(row["Close"] - row["Open"]) / open_price
        range_pct = (row["High"] - row["Low"]) / open_price

        cond = (
            row["Close"] > row["VWAP"] and
            row["Volume"] > 500000 and
            row["Volume"] > (2 * row["VOL_SMA20"]) and
            body_pct > 0.006 and
            range_pct > 0.006 and
            row["Close"] > row["Open"]
        )

        if cond:
            radar_time = df.index[i] + pd.Timedelta(minutes=15)

            radars.append({
                "time": radar_time,
                "close": round(float(row["Close"]), 2)
            })

    return radars


# =====================================
# 5M ENTRY
# =====================================

def find_5m_trade(df5, radar_time):
    if df5 is None or df5.empty:
        return None

    df = df5.copy()

    # only after 15m candle close
    df = df[df.index > radar_time]

    if df.empty:
        return None

    df["VWAP"] = calculate_vwap(df)

    for i in range(len(df)):
        row = df.iloc[i]

        if pd.isna(row["VWAP"]):
            continue

        vwap_touch = (
            float(row["Low"]) <= float(row["VWAP"]) <= float(row["High"])
        )

        bullish = float(row["Close"]) > float(row["Open"])

        if vwap_touch and bullish:

            entry = round(float(row["High"]), 2)
            sl = round(float(row["VWAP"]), 2)
            actual_risk = round(entry - sl, 2)

            if actual_risk <= 0:
                continue
            min_risk = round(entry * 0.002, 2)

            if actual_risk < min_risk:
                continue
            max_risk = round(entry * 0.005, 2)

            if actual_risk > max_risk:
                continue
                
            target = round(entry + (actual_risk * 2), 2)    

            # =========================
            # RESULT CHECK (WIN / LOSS / OPEN)
            # =========================

            result = "OPEN"

            future_df = df.iloc[i:]

            for _, next_row in future_df.iterrows():

                hit_sl = float(next_row["Low"]) <= sl
                hit_target = float(next_row["High"]) >= target

                if hit_target and hit_sl:
                    result = "OPEN"
                    break

                elif hit_target:
                    result = "WIN"
                    break

                elif hit_sl:
                    result = "LOSS"
                    break

            return {
                "time": df.index[i],
                "entry": entry,
                "sl": sl,
                "target": target,
                "result": result
            }

    return None

# =====================================
# SINGLE SCAN
# =====================================

def scan_stock(symbol, date=None):
    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return None

    df15 = session_filter(df15)
    df5 = session_filter(df5)

    if df15 is None:
        return None

    # Find ALL radar candles
    radars = find_15m_radars(df15)

    if not radars:
        return None

    selected_radar = None

    for radar in radars:
        radar_time = radar["time"]

        # if specific date requested
        if date:
            target_date = pd.to_datetime(date).date()

            if radar_time.date() != target_date:
                continue

        selected_radar = radar
        break

    if not selected_radar:
        return None

    radar_time = selected_radar["time"]

    trade = None

    if df5 is not None:
        temp5 = filter_date(df5, radar_time.strftime("%Y-%m-%d"))

        if temp5 is not None:
            trade = find_5m_trade(temp5, radar_time)

    return {
        "symbol": symbol,
        "radar": {
            "time": radar_time
        },
        "trade": trade
    }


# =====================================
# RANGE SCAN
# =====================================

def run_range(symbol, d1, d2):
    df15 = to_ist(get_data(symbol, "15m"))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return []

    df15 = session_filter(df15)
    df5 = session_filter(df5)

    if df15 is None:
        return []

    start_date = pd.to_datetime(d1).date()
    end_date = pd.to_datetime(d2).date()

    results = []

    # VERY IMPORTANT:
    # find ALL radar candles from full df
    radars = find_15m_radars(df15)

    if not radars:
        return []

    for radar in radars:
        radar_time = radar["time"]
        radar_date = radar_time.date()

        # date range filter
        if not (start_date <= radar_date <= end_date):
            continue

        trade = None

        if df5 is not None:
            temp5 = filter_date(
                df5,
                radar_time.strftime("%Y-%m-%d")
            )

            if temp5 is not None:
                trade = find_5m_trade(temp5, radar_time)

        results.append({
            "symbol": symbol,
            "radar": {
                "time": radar_time
            },
            "trade": trade
        })

    return results


# =====================================
# ALL SCAN
# =====================================

def scan_all(scan_date=None):
    results = []

    for stock in FNO_STOCKS:
        result = scan_stock(stock, scan_date)

        if result:
            results.append(result)

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

    today = datetime.now().strftime("%Y-%m-%d")

    if text == "LIVE":
        send(chat_id, "📡 LIVE SCANNING")

        results = scan_all(today)

        if not results:
            send(chat_id, "No live setups found")
            return "ok"

        for r in results:
            send(chat_id, format_result(r))

        return "ok"

    if text == "RADAR TODAY":
        send(chat_id, "📊 RADAR TODAY")

        results = scan_all(today)

        if not results:
            send(chat_id, "No radar found today")
            return "ok"

        for r in results:
            send(chat_id, f"{r['symbol']} → {r['radar']['time']}")

        return "ok"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR", text):
        scan_date = text.replace(" RADAR", "")

        send(chat_id, f"📊 RADAR {scan_date}")

        results = scan_all(scan_date)

        if not results:
            send(chat_id, "No radar setups found")
            return "ok"

        for r in results:
            send(chat_id, f"{r['symbol']} → {r['radar']['time']}")

        return "ok"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        send(chat_id, f"📅 SCANNING {text}")

        results = scan_all(text)

        if not results:
            send(chat_id, "No setups found")
            return "ok"

        for r in results:
            send(chat_id, format_result(r))

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
            send(chat_id, format_result(r))

        return "ok"

    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
        sym, scan_date = text.split()
        symbol = sym + ".NS"

        send(chat_id, f"📊 SCANNING {symbol}")

        result = scan_stock(symbol, scan_date)

        if result:
            send(chat_id, format_result(result))
        else:
            send(chat_id, "No setup found")

        return "ok"

    if text == "/START":
        send(
            chat_id,
            "🤖 HYBRID FNO BOT READY\n\n"
            "Commands:\n"
            "LIVE\n"
            "RADAR TODAY\n"
            "2026-04-06\n"
            "BHEL 2026-04-06\n"
            "BHEL 2026-04-06 TO 2026-04-10\n"
            "2026-04-06 RADAR"
        )
        return "ok"

    send(chat_id, "Unknown command")
    return "ok"


@app.route("/")
def home():
    return "BOT RUNNING"


if __name__ == "__main__":
    print("🚀 BOT STARTING")

    set_webhook()

    app.run(
        host="0.0.0.0",
        port=PORT
    )
