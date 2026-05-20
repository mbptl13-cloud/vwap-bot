# ================= IMPORTS =================

import time
import datetime
import pytz
import asyncio
import threading
import os
import requests
import pandas as pd
import pyotp

from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from telegram import Bot
from flask import Flask, request

# ================= CONFIG =================

API_KEY = "ccsipvbP"
CLIENT_ID = "M50717452"
PASSWORD = "2329"
TOTP_SECRET = "3QCEGXTQKFN6BNHP76N7P3QZAY"

TOKEN = "8944295593:AAHXYIQcXVr5BSt1ilwjUoKp59v9knVNG70"
CHAT_ID = 309248606

bot = Bot(token=TOKEN)

app = Flask(__name__)

# ================= GLOBAL =================

TOKENS = {}
TOKEN_MAP = {}

FEED_TOKEN = None
JWT = None

angel = None

scan_running = False
scan_started_at = None

active_radar = {}
trades = {}

live_price = {}
radar_history = {}

# ================= LOGIN =================

def login():

    print("🔐 LOGGING IN...")

    obj = SmartConnect(api_key=API_KEY)

    totp = pyotp.TOTP(
        TOTP_SECRET
    ).now()

    data = obj.generateSession(
        CLIENT_ID,
        PASSWORD,
        totp
    )

    feed = data["data"]["feedToken"]

    jwt = data["data"]["jwtToken"]

    return obj, feed, jwt

# ================= TELEGRAM =================

async def send(msg):

    try:

        await bot.send_message(
            chat_id=CHAT_ID,
            text=msg
        )

    except Exception as e:

        print("❌ TELEGRAM:", e)

# ================= VWAP =================

def vwap(df):

    df["tp"] = (
        df["high"] +
        df["low"] +
        df["close"]
    ) / 3

    df["cv"] = (
        df["volume"]
        .cumsum()
    )

    df["cpv"] = (
        df["tp"] *
        df["volume"]
    ).cumsum()

    df["vwap"] = (
        df["cpv"] /
        df["cv"]
    )

    return df

# ================= TOKEN FETCH =================

def get_fno_tokens():

    print("🔄 FETCHING FNO STOCKS...")

    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

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

        print("❌ TOKEN ERROR:", e)

        return {}, {}

    fno_symbols = set()

    for i in data:

        try:

            if i.get("exch_seg") == "NFO":

                name = i.get("name")

                if name:
                    fno_symbols.add(name)

        except:
            pass

    tokens = {}
    token_map = {}

    for i in data:

        try:

            if (
                i.get("exch_seg") == "NSE"
                and
                i.get("symbol", "").endswith("-EQ")
            ):

                sym = i["symbol"].replace("-EQ", "")

                if sym not in fno_symbols:
                    continue

                tok = str(i["token"])

                tokens[sym] = tok

                token_map[tok] = sym

        except:
            pass

    print(f"✅ TOTAL FNO STOCKS: {len(tokens)}")

    return tokens, token_map

# ================= REFRESH TOKENS =================

def refresh_tokens():

    global TOKENS
    global TOKEN_MAP

    ist = pytz.timezone("Asia/Kolkata")

    while True:

        try:

            now = datetime.datetime.now(ist)

            if now.hour == 8 and now.minute == 45:

                TOKENS, TOKEN_MAP = get_fno_tokens()

                print("🔁 TOKENS UPDATED")

                time.sleep(60)

            time.sleep(20)

        except Exception as e:

            print("❌ REFRESH:", e)

            time.sleep(20)

# ================= CANDLE DATA =================

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

        df["time"] = pd.to_datetime(
            df["time"]
        )

        try:

            df["time"] = (
                df["time"]
                .dt.tz_localize(None)
            )

        except:
            pass

        for col in [
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]:

            df[col] = pd.to_numeric(
                df[col]
            )

        return df

    except Exception as e:

        print("❌ CANDLE:", e)

        return None

# ================= RADAR =================

def radar():

    global scan_running
    global scan_started_at
    global radar_history
    global active_radar

    try:

        scan_running = True

        scan_started_at = datetime.datetime.now(
            pytz.timezone("Asia/Kolkata")
        )

        radar_history = {}
        active_radar = {}

        print("📡 RUNNING RADAR...")

        for sym, token in TOKENS.items():

            if not scan_running:

                asyncio.run(
                    send("🛑 SCAN STOPPED")
                )

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

                    # ================= TODAY FILTER =================

                    today = datetime.datetime.now(
                        pytz.timezone("Asia/Kolkata")
                    ).date()

                    if candle_time.date() != today:
                        continue

                    # ================= TIME FILTER =================

                    if candle_time.hour < 9:
                        continue

                    if (
                        candle_time.hour == 9
                        and
                        candle_time.minute < 30
                    ):
                        continue

                    if candle_time.hour > 13:
                        continue

                    if (
                        candle_time.hour == 13
                        and
                        candle_time.minute > 45
                    ):
                        continue

                    # ================= ORIGINAL TIGHT CONDITIONS =================

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
                            (
                                row["high"] -
                                row["low"]
                            ) /
                            row["open"]
                        ) * 100
                    )

                    range_cond = (
                        range_percent > 1
                    )

                    body_percent = (
                        (
                            abs(
                                row["close"] -
                                row["open"]
                            ) /
                            row["open"]
                        ) * 100
                    )

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

                        print(
                            f"📡 RADAR: "
                            f"{sym} "
                            f"{candle_time.strftime('%H:%M')}"
                        )

            except Exception as e:

                print(f"❌ {sym}:", e)

        # ================= MESSAGE =================

        time_map = {}

        for k, r in radar_history.items():

            t = r["time"]

            if t not in time_map:
                time_map[t] = []

            time_map[t].append(
                r["symbol"]
            )

        msg = "📡 RADAR SIGNALS\n\n"

        start_time = datetime.datetime.strptime(
            "09:30",
            "%H:%M"
        )

        now_ist = datetime.datetime.now(
            pytz.timezone("Asia/Kolkata")
        )

        current = start_time

        while current.time() <= now_ist.time():

            t = current.strftime("%H:%M")

            msg += f"⏰ {t}\n"

            if t in time_map:

                for s in sorted(time_map[t]):

                    msg += f"• {s}\n"

            else:

                msg += "❌ NO STOCK\n"

            msg += "\n"

            current += datetime.timedelta(
                minutes=15
            )

        asyncio.run(send(msg))

        time.sleep(2)

        scan_running = False

    except Exception as e:

        scan_running = False

        print("❌ RADAR ERROR:", e)

# ================= ENTRY =================

def entry():

    now = datetime.datetime.now(
        pytz.timezone("Asia/Kolkata")
    )

    if not (
        datetime.time(9,45)
        <=
        now.time()
        <=
        datetime.time(14,0)
    ):
        return

    for sym in active_radar:

        if sym in trades:
            continue

        try:

            r = active_radar[sym]

            radar_time = datetime.datetime.strptime(
                r["time"],
                "%H:%M"
            ).time()

            radar_dt = datetime.datetime.combine(
                now.date(),
                radar_time
            )

            next_allowed_entry = (
                radar_dt +
                datetime.timedelta(minutes=15)
            ).time()

            if now.time() < next_allowed_entry:
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

            # ================= ENTRY NEAR VWAP =================

            distance_from_vwap = (
                (
                    last["close"] -
                    last["vwap"]
                ) /
                last["vwap"]
            ) * 100

            if (

                last["close"] > last["vwap"]

                and

                prev["low"] <= prev["vwap"] * 1.001

                and

                distance_from_vwap <= 0.3

            ):

                # ================= VWAP SL =================

                sl_price = (
                    last["vwap"] * 0.997
                )

                risk = (
                    last["close"] -
                    sl_price
                )

                # ================= 1:2 TARGET =================

                target_price = (
                    last["close"] +
                    (risk * 2)
                )

                trades[sym] = {

                    "date":
                        now.strftime("%Y-%m-%d"),

                    "radar":
                        r["time"],

                    "entry":
                        now.strftime("%H:%M"),

                    "entry_price":
                        last["close"],

                    "sl":
                        sl_price,

                    "tgt":
                        target_price,

                    "status":
                        "OPEN"

                }

                asyncio.run(
                    send(
                        f"🚀 ENTRY ALERT 🚀\n\n"

                        f"📈 STOCK: {sym}\n"

                        f"📡 RADAR: {r['time']}\n"

                        f"⏰ ENTRY: {now.strftime('%H:%M')}\n"

                        f"💰 PRICE: {round(last['close'], 2)}\n"

                        f"📊 VWAP: {round(last['vwap'], 2)}\n"

                        f"🛑 STOPLOSS: {round(sl_price, 2)}\n"

                        f"🎯 TARGET: {round(target_price, 2)}"
                    )
                )

        except Exception as e:

            print(f"❌ ENTRY {sym}:", e)

# ================= RESULT =================

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

                asyncio.run(
                    send(
                        f"❌ SL HIT\n\n"
                        f"📈 STOCK: {sym}\n"
                        f"🛑 SL: {round(t['sl'],2)}"
                    )
                )

            elif last["high"] >= t["tgt"]:

                t["status"] = "WIN"

                asyncio.run(
                    send(
                        f"🎯 TARGET HIT\n\n"
                        f"📈 STOCK: {sym}\n"
                        f"🎯 TARGET: {round(t['tgt'],2)}"
                    )
                )

        except Exception as e:

            print(f"❌ RESULT {sym}:", e)

# ================= LOOP =================

def loop():

    ist = pytz.timezone("Asia/Kolkata")

    last = None

    while True:

        try:

            now = datetime.datetime.now(ist)

            if (
                datetime.time(9,45)
                <=
                now.time()
                <=
                datetime.time(15,0)
            ):

                if now.minute % 5 == 0:

                    key = now.strftime("%H:%M")

                    if key != last:

                        last = key

                        print(
                            f"🚀 LIVE CHECK {key}"
                        )

                        entry()

                        result()

            time.sleep(2)

        except Exception as e:

            print("❌ LOOP:", e)

            time.sleep(5)

# ================= WEBSOCKET =================

def subscribe_dynamic(sws, tokens):

    batch_size = 50

    for i in range(
        0,
        len(tokens),
        batch_size
    ):

        sws.subscribe([
            {
                "exchangeType": 1,
                "tokens": tokens[i:i+batch_size]
            }
        ])

        time.sleep(0.5)

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

                except:
                    pass

            sws.on_open = on_open
            sws.on_data = on_data

            sws.connect()

        except Exception as e:

            print("❌ SOCKET:", e)

            time.sleep(5)

# ================= HOME =================

@app.route("/", methods=["GET"])
def home():

    return "BOT RUNNING", 200

# ================= WEBHOOK =================

@app.route("/", methods=["POST"])
def webhook():

    global scan_running

    try:

        data = request.get_json()

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

        if text == "RADAR":

            if scan_running:

                asyncio.run(
                    send(
                        "⚠ SCAN ALREADY RUNNING"
                    )
                )

            else:

                threading.Thread(
                    target=radar,
                    daemon=True
                ).start()

                asyncio.run(
                    send(
                        "📡 RADAR SCAN STARTED"
                    )
                )

        elif text == "LIVE":

            if not trades:

                asyncio.run(
                    send(
                        "❌ NO ACTIVE TRADES"
                    )
                )

            else:

                msg = "🚀 LIVE TRADES\n\n"

                for sym, t in trades.items():

                    msg += (
                        f"📈 {sym}\n"
                        f"ENTRY: {round(t['entry_price'],2)}\n"
                        f"SL: {round(t['sl'],2)}\n"
                        f"TGT: {round(t['tgt'],2)}\n"
                        f"STATUS: {t['status']}\n\n"
                    )

                asyncio.run(send(msg))

        elif text == "STOP":

            scan_running = False

            asyncio.run(
                send(
                    "🛑 STOP COMMAND RECEIVED"
                )
            )

        elif text == "STATUS":

            if scan_running:

                runtime = ""

                if scan_started_at:

                    runtime = (
                        datetime.datetime.now(
                            pytz.timezone("Asia/Kolkata")
                        ) - scan_started_at
                    )

                    runtime = str(runtime).split(".")[0]

                msg = (
                    "📡 SCAN RUNNING\n\n"
                    f"⏱ RUNTIME: {runtime}"
                )

            else:

                msg = "✅ IDLE"

            asyncio.run(send(msg))

        else:

            asyncio.run(
                send(
                    "AVAILABLE COMMANDS:\n\n"
                    "RADAR\n"
                    "LIVE\n"
                    "STOP\n"
                    "STATUS"
                )
            )

        return "ok", 200

    except Exception as e:

        print("❌ WEBHOOK:", e)

        return "error", 200

# ================= MAIN =================

if __name__ == "__main__":

    print("🚀 BOT STARTING...")

    try:

        angel, FEED_TOKEN, JWT = login()

        print("✅ LOGIN SUCCESS")

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

        print("🔌 SYSTEM RUNNING")

        port = int(
            os.environ.get("PORT", 10000)
        )

        app.run(
            host="0.0.0.0",
            port=port
        )

    except Exception as e:

        print("❌ CRASH:", e)
