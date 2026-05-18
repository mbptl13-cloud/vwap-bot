import time
import datetime
import pytz
import threading
import os
import requests
import pandas as pd
import pyotp

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from telegram import Bot
from flask import Flask, request

# =========================================================
# CONFIG
# =========================================================

API_KEY = "ccsipvbP"
CLIENT_ID = "M50717452"
PASSWORD = "2329"
TOTP_SECRET = "3QCEGXTQKFN6BNHP76N7P3QZAY"

TOKEN = "8944295593:AAHXYIQcXVr5BSt1ilwjUoKp59v9knVNG70"
CHAT_ID = 309248606

bot = Bot(token=TOKEN)

app = Flask(__name__)

# =========================================================
# GLOBALS
# =========================================================

TOKENS = {}
TOKEN_MAP = {}

FEED_TOKEN = None
JWT = None

angel = None

scan_running = False

active_radar = {}
trades = {}

live_price = {}
radar_history = {}

# =========================================================
# LOGIN
# =========================================================

def login():

    try:

        print("🔐 LOGGING IN...")

        obj = SmartConnect(api_key=API_KEY)

        totp = pyotp.TOTP(TOTP_SECRET).now()

        data = obj.generateSession(
            CLIENT_ID,
            PASSWORD,
            totp
        )

        if not data.get("status"):
            raise Exception(data)

        feed = data["data"]["feedToken"]
        jwt = data["data"]["jwtToken"]

        print("✅ LOGIN SUCCESS")

        return obj, feed, jwt

    except Exception as e:

        print("❌ LOGIN FAILED:", e)

        raise e

# =========================================================
# TELEGRAM
# =========================================================

def send(msg):

    try:

        bot.send_message(
            chat_id=CHAT_ID,
            text=msg
        )

        print("📤 TELEGRAM SENT")

    except Exception as e:

        print("❌ TELEGRAM ERROR:", e)

# =========================================================
# VWAP
# =========================================================

def vwap(df):

    df = df.copy()

    df["tp"] = (
        df["high"] +
        df["low"] +
        df["close"]
    ) / 3

    df["cv"] = df["volume"].cumsum()

    df["cpv"] = (
        df["tp"] *
        df["volume"]
    ).cumsum()

    df["vwap"] = (
        df["cpv"] /
        df["cv"]
    )

    return df

# =========================================================
# FETCH FNO TOKENS
# =========================================================

def get_fno_tokens():

    print("🔄 FETCHING FNO STOCKS...")

    url = (
        "https://margincalculator.angelbroking.com/"
        "OpenAPI_File/files/OpenAPIScripMaster.json"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        data = response.json()

    except Exception as e:

        print("❌ TOKEN FETCH ERROR:", e)

        return {}, {}

    fno_symbols = set()

    for item in data:

        try:

            if item.get("exch_seg") == "NFO":

                name = item.get("name")

                if name:
                    fno_symbols.add(name)

        except:
            pass

    tokens = {}
    token_map = {}

    for item in data:

        try:

            if (
                item.get("exch_seg") == "NSE"
                and
                item.get("symbol", "").endswith("-EQ")
            ):

                sym = item["symbol"].replace("-EQ", "")

                if sym not in fno_symbols:
                    continue

                tok = str(item["token"])

                tokens[sym] = tok
                token_map[tok] = sym

        except:
            pass

    print(f"✅ TOTAL FNO STOCKS: {len(tokens)}")

    return tokens, token_map

# =========================================================
# REFRESH TOKENS DAILY
# =========================================================

def refresh_tokens():

    global TOKENS
    global TOKEN_MAP

    ist = pytz.timezone("Asia/Kolkata")

    while True:

        try:

            now = datetime.datetime.now(ist)

            if now.hour == 8 and now.minute == 45:

                TOKENS, TOKEN_MAP = get_fno_tokens()

                print("🔁 TOKENS REFRESHED")

                time.sleep(60)

            time.sleep(20)

        except Exception as e:

            print("❌ REFRESH ERROR:", e)

            time.sleep(20)

# =========================================================
# CANDLE DATA
# =========================================================

def get_candle_data(token, interval):

    global angel

    try:

        ist = pytz.timezone("Asia/Kolkata")

        now = datetime.datetime.now(ist)

        from_date = (
            now -
            datetime.timedelta(days=5)
        ).strftime("%Y-%m-%d 09:15")

        to_date = now.strftime("%Y-%m-%d %H:%M")

        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }

        data = angel.getCandleData(params)

        candles = data.get("data")

        if not candles:
            return None

        df = pd.DataFrame(
            candles,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        )

        df["time"] = pd.to_datetime(df["time"])

        for col in [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]:
            df[col] = pd.to_numeric(df[col])

        return df

    except Exception as e:

        print("❌ CANDLE ERROR:", e)

        return None

# =========================================================
# RADAR SCAN
# =========================================================

def radar():

    global scan_running
    global radar_history
    global active_radar

    try:

        scan_running = True

        radar_history = {}
        active_radar = {}

        count = 0

        print("📡 RUNNING RADAR...")

        ist = pytz.timezone("Asia/Kolkata")

        today = datetime.datetime.now(ist).date()

        for sym, token in TOKENS.items():

            if not scan_running:

                send("🛑 SCAN STOPPED")

                return

            try:

                df = get_candle_data(
                    token,
                    "FIFTEEN_MINUTE"
                )

                if df is None:
                    continue

                if len(df) < 20:
                    continue

                df = vwap(df)

                df["vol_sma20"] = (
                    df["volume"]
                    .rolling(20)
                    .mean()
                )

                for i in range(len(df)):

                    row = df.iloc[i]

                    candle_time = row["time"]

                    if candle_time.date() != today:
                        continue

                    if candle_time.hour < 9:
                        continue

                    if candle_time.hour == 9 and candle_time.minute < 30:
                        continue

                    if candle_time.hour > 13:
                        continue

                    if candle_time.hour == 13 and candle_time.minute > 30:
                        continue

                    volume_cond = (
                        row["volume"] > 500000
                    )

                    turnover_cond = (
                        (
                            row["close"] *
                            row["volume"]
                        ) > 15000000
                    )

                    range_percent = (
                        (
                            row["high"] -
                            row["low"]
                        ) /
                        row["open"]
                    ) * 100

                    range_cond = (
                        range_percent > 1
                    )

                    body_percent = (
                        abs(
                            row["close"] -
                            row["open"]
                        ) /
                        row["open"]
                    ) * 100

                    body_cond = (
                        body_percent > 0.6
                    )

                    vwap_cond = (
                        row["close"] >
                        row["vwap"]
                    )

                    volume_blast_cond = (
                        row["volume"] >
                        (
                            row["vol_sma20"] * 2
                        )
                    )

                    bullish_cond = (
                        row["close"] >
                        row["open"]
                    )

                    if (

                        volume_cond
                        and
                        turnover_cond
                        and
                        range_cond
                        and
                        body_cond
                        and
                        vwap_cond
                        and
                        volume_blast_cond
                        and
                        bullish_cond

                    ):

                        key = (
                            sym +
                            "_" +
                            candle_time.strftime("%H:%M")
                        )

                        if key in radar_history:
                            continue

                        radar_history[key] = {

                            "symbol":
                                sym,

                            "time":
                                candle_time.strftime("%H:%M"),

                            "high":
                                row["high"],

                            "low":
                                row["low"],

                            "close":
                                row["close"]

                        }

                        active_radar[sym] = radar_history[key]

                        count += 1

                        print(
                            f"📡 RADAR: "
                            f"{sym} "
                            f"{candle_time.strftime('%H:%M')}"
                        )

            except Exception as e:

                print(f"❌ {sym} ERROR:", e)

        scan_running = False

        if count == 0:

            send("❌ NO RADAR FOUND")

        else:

            time_map = {}

            for _, r in radar_history.items():

                t = r["time"]

                if t not in time_map:
                    time_map[t] = []

                time_map[t].append(r["symbol"])

            sorted_times = sorted(
                time_map.keys(),
                key=lambda x: datetime.datetime.strptime(
                    x,
                    "%H:%M"
                )
            )

            msg = "📡 RADAR SIGNALS\n\n"

            for t in sorted_times:

                msg += f"⏰ {t}\n"

                for s in sorted(time_map[t]):

                    msg += f"• {s}\n"

                msg += "\n"

            send(msg)

    except Exception as e:

        scan_running = False

        print("❌ RADAR ERROR:", e)

# =========================================================
# ENTRY
# =========================================================

def entry():

    now = datetime.datetime.now(
        pytz.timezone("Asia/Kolkata")
    )

    if not (
        datetime.time(9,45)
        <=
        now.time()
        <=
        datetime.time(13,45)
    ):
        return

    for sym in active_radar:

        try:

            if sym in trades:
                continue

            r = active_radar[sym]

            radar_time = datetime.datetime.strptime(
                r["time"],
                "%H:%M"
            ).time()

            radar_dt = datetime.datetime.combine(
                now.date(),
                radar_time
            )

            next_entry = (
                radar_dt +
                datetime.timedelta(minutes=15)
            ).time()

            if now.time() < next_entry:
                continue

            token = TOKENS[sym]

            df = get_candle_data(
                token,
                "FIVE_MINUTE"
            )

            if df is None:
                continue

            if len(df) < 10:
                continue

            df = vwap(df)

            last = df.iloc[-1]
            prev = df.iloc[-2]

            if (
                last["close"] > last["vwap"]
                and
                prev["low"] <= prev["vwap"] * 1.002
            ):

                sl = min(
                    prev["low"],
                    r["low"]
                )

                entry_price = last["close"]

                target = (
                    entry_price +
                    (
                        entry_price - sl
                    )
                )

                trades[sym] = {

                    "date":
                        now.strftime("%Y-%m-%d"),

                    "radar":
                        r["time"],

                    "entry":
                        now.strftime("%H:%M"),

                    "entry_price":
                        entry_price,

                    "sl":
                        sl,

                    "tgt":
                        target,

                    "status":
                        "OPEN"

                }

                send(

                    f"🚀 ENTRY ALERT\n\n"
                    f"STOCK: {sym}\n"
                    f"RADAR: {r['time']}\n"
                    f"ENTRY: {now.strftime('%H:%M')}\n"
                    f"PRICE: {round(entry_price,2)}"

                )

        except Exception as e:

            print(f"❌ ENTRY ERROR {sym}:", e)

# =========================================================
# RESULT
# =========================================================

def result():

    for sym, t in trades.items():

        try:

            if t["status"] != "OPEN":
                continue

            token = TOKENS[sym]

            df = get_candle_data(
                token,
                "FIVE_MINUTE"
            )

            if df is None:
                continue

            last = df.iloc[-1]

            if last["low"] <= t["sl"]:

                t["status"] = "LOSS"

                send(
                    f"❌ SL HIT\n\n"
                    f"STOCK: {sym}"
                )

            elif last["high"] >= t["tgt"]:

                t["status"] = "WIN"

                send(
                    f"🎯 TARGET HIT\n\n"
                    f"STOCK: {sym}"
                )

        except Exception as e:

            print(f"❌ RESULT ERROR {sym}:", e)

# =========================================================
# REPORT
# =========================================================

def report():

    out = []

    if trades:

        out.append("🚀 TRADES\n")

        sorted_trades = sorted(
            trades.items(),
            key=lambda x: datetime.datetime.strptime(
                x[1]["entry"],
                "%H:%M"
            )
        )

        for sym, t in sorted_trades:

            out.append(

f"""📊 {sym}

📡 RADAR: {t['radar']}
🚀 ENTRY: {t['entry']}

💰 ENTRY: {round(t['entry_price'],2)}
🛑 SL: {round(t['sl'],2)}
🎯 TARGET: {round(t['tgt'],2)}

📌 STATUS: {t['status']}

━━━━━━━━━━━━━━━"""

            )

    if not out:
        return "❌ NO SIGNALS TODAY"

    return "\n".join(out)

# =========================================================
# LOOP
# =========================================================

def loop():

    ist = pytz.timezone("Asia/Kolkata")

    last = None

    while True:

        try:

            now = datetime.datetime.now(ist)

            if (
                datetime.time(9,15)
                <=
                now.time()
                <=
                datetime.time(15,30)
            ):

                if now.minute % 5 == 0:

                    key = now.strftime("%H:%M")

                    if key != last:

                        last = key

                        print(f"⏰ LOOP: {key}")

                        entry()

                        result()

            time.sleep(5)

        except Exception as e:

            print("❌ LOOP ERROR:", e)

            time.sleep(5)

# =========================================================
# WEBSOCKET
# =========================================================

def subscribe_dynamic(sws, tokens):

    batch_size = 50

    for i in range(0, len(tokens), batch_size):

        batch = tokens[i:i+batch_size]

        sws.subscribe(
            "abc",
            1,
            [
                {
                    "exchangeType": 1,
                    "tokens": batch
                }
            ]
        )

        time.sleep(1)

def socket():

    global FEED_TOKEN
    global JWT

    while True:

        try:

            print("🔌 STARTING WEBSOCKET...")

            sws = SmartWebSocketV2(
                JWT,
                API_KEY,
                CLIENT_ID,
                FEED_TOKEN
            )

            def on_open(ws):

                print("✅ SOCKET CONNECTED")

                tokens = list(
                    TOKENS.values()
                )[:150]

                subscribe_dynamic(
                    sws,
                    tokens
                )

            def on_data(ws, msg):

                try:

                    token = str(
                        msg.get("token")
                    )

                    price = (
                        msg.get(
                            "last_traded_price",
                            0
                        ) / 100
                    )

                    if token in TOKEN_MAP:

                        sym = TOKEN_MAP[token]

                        live_price[sym] = price

                except Exception as e:

                    print("❌ SOCKET DATA:", e)

            def on_error(ws, error):

                print("❌ SOCKET ERROR:", error)

            def on_close(ws):

                print("🔴 SOCKET CLOSED")

            sws.on_open = on_open
            sws.on_data = on_data
            sws.on_error = on_error
            sws.on_close = on_close

            sws.connect()

        except Exception as e:

            print("❌ SOCKET CRASH:", e)

        time.sleep(10)

# =========================================================
# HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return "BOT RUNNING", 200

# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    global scan_running

    try:

        data = request.get_json()

        print("📩 REQUEST:", data)

        if not data:
            return "ok", 200

        text = (
            data
            .get("message", {})
            .get("text", "")
            .strip()
            .upper()
        )

        print("📩 COMMAND:", text)

        if text == "LIVE":

            send(report())

        elif text == "RADAR":

            if scan_running:

                send("⚠ SCAN ALREADY RUNNING")

            else:

                threading.Thread(
                    target=radar,
                    daemon=True
                ).start()

                send("📡 RADAR SCAN STARTED")

        elif text == "STOP":

            scan_running = False

            send("🛑 STOP COMMAND RECEIVED")

        elif text == "STATUS":

            if scan_running:

                send("📡 SCAN RUNNING")

            else:

                send("✅ IDLE")

        else:

            send(

                "AVAILABLE COMMANDS:\n\n"
                "RADAR\n"
                "LIVE\n"
                "STOP\n"
                "STATUS"

            )

        return "ok", 200

    except Exception as e:

        print("❌ WEBHOOK ERROR:", e)

        return "error", 200

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("🚀 BOT STARTING...")

    try:

        angel, FEED_TOKEN, JWT = login()

        TOKENS, TOKEN_MAP = get_fno_tokens()

        threading.Thread(
            target=socket,
            daemon=True
        ).start()

        threading.Thread(
            target=loop,
            daemon=True
        ).start()

        threading.Thread(
            target=refresh_tokens,
            daemon=True
        ).start()

        print("✅ SYSTEM RUNNING")

        port = int(
            os.environ.get("PORT", 10000)
        )

        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            threaded=True
        )

    except Exception as e:

        print("❌ MAIN CRASH:", e)
