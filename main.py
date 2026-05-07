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

TOKEN = "8602800906:AAHTYNJ-96TXL6Mi8xDvS5VRw1ewy_sDBXY"
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

candles_15m = {}
candles_5m = {}

active_radar = {}
trades = {}

live_price = {}

# ================= LOGIN =================

def login():

    print("🔐 Logging in...")

    obj = SmartConnect(api_key=API_KEY)

    totp = pyotp.TOTP(TOTP_SECRET).now()

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

# ================= FNO TOKEN FETCH =================

def get_fno_tokens():

    print("🔄 Fetching ONLY FNO Stocks...")

    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        data = requests.get(
            url,
            headers=headers,
            timeout=30
        ).json()

    except Exception as e:

        print("❌ TOKEN ERROR:", e)

        return {}, {}

    # ================= FIND FNO SYMBOLS =================

    fno_symbols = set()

    for i in data:

        try:

            if i.get("exch_seg") == "NFO":

                name = i.get("name")

                if name:
                    fno_symbols.add(name)

        except:
            pass

    print(f"✅ FNO SYMBOLS: {len(fno_symbols)}")

    # ================= NSE TOKENS =================

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

    print(f"✅ FINAL FNO STOCKS: {len(tokens)}")

    return tokens, token_map

# ================= REFRESH TOKENS =================

def refresh_tokens():

    global TOKENS
    global TOKEN_MAP

    ist = pytz.timezone("Asia/Kolkata")

    while True:

        now = datetime.datetime.now(ist)

        if now.hour == 8 and now.minute == 45:

            TOKENS, TOKEN_MAP = get_fno_tokens()

            print("🔁 TOKENS UPDATED")

            time.sleep(60)

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

        print("❌ CANDLE:", e)

        return None

# ================= RADAR =================

def radar():

    global scan_running

    try:

        scan_running = True

        active_radar.clear()

        count = 0

        print("📡 RUNNING RADAR...")

        for sym, token in TOKENS.items():

            if not scan_running:

                print("🛑 SCAN STOPPED")

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

                last = df.iloc[-1]

                # ================= YOUR ORIGINAL CONDITIONS =================

                volume_cond = (
                    last["volume"] > 500000
                )

                turnover_cond = (
                    (
                        last["close"]
                        *
                        last["volume"]
                    ) > 15000000
                )

                range_percent = (
                    (
                        (
                            last["high"]
                            -
                            last["low"]
                        )
                        /
                        last["open"]
                    ) * 100
                )

                range_cond = (
                    range_percent > 1
                )

                body_percent = (
                    (
                        abs(
                            last["close"]
                            -
                            last["open"]
                        )
                        /
                        last["open"]
                    ) * 100
                )

                body_cond = (
                    body_percent > 0.6
                )

                vwap_cond = (
                    last["close"]
                    >
                    last["vwap"]
                )

                volume_blast_cond = (
                    last["volume"]
                    >
                    (
                        last["vol_sma20"] * 2
                    )
                )

                bullish_cond = (
                    last["close"]
                    >
                    last["open"]
                )

                # ================= FINAL RADAR =================

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

                    active_radar[sym] = {

                        "time":
                            last["time"],

                        "high":
                            last["high"],

                        "low":
                            last["low"],

                        "close":
                            last["close"]

                    }

                    count += 1

                    print(f"📡 RADAR FOUND: {sym}")

                    asyncio.run(
                        send(
                            f"📡 RADAR FOUND\n\n"
                            f"STOCK: {sym}\n"
                            f"CLOSE: {round(last['close'],2)}"
                        )
                    )

            except Exception as e:

                print(f"❌ {sym}:", e)

        scan_running = False

        if count == 0:

            asyncio.run(
                send("❌ NO RADAR FOUND")
            )

        else:

            asyncio.run(
                send(
                    f"✅ RADAR COMPLETE\n"
                    f"TOTAL: {count}"
                )
            )

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
        datetime.time(13,30)
    ):
        return

    for sym in active_radar:

        if sym in trades:
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

        r = active_radar[sym]

        # ================= YOUR ORIGINAL 5M CONDITION =================

        if (
            last["close"] > last["vwap"]
            and
            prev["low"] <= prev["vwap"] * 1.002
        ):

            trades[sym] = {

                "date":
                    now.strftime("%Y-%m-%d"),

                "radar":
                    r["time"].strftime("%H:%M"),

                "entry":
                    now.strftime("%H:%M"),

                "entry_price":
                    last["close"],

                "sl":
                    min(
                        prev["low"],
                        r["low"]
                    ),

                "tgt":
                    last["close"] +
                    (
                        last["close"]
                        -
                        min(
                            prev["low"],
                            r["low"]
                        )
                    ),

                "status":
                    "OPEN"

            }

            asyncio.run(
                send(
                    f"🚀 ENTRY ALERT\n\n"
                    f"STOCK: {sym}\n"
                    f"ENTRY: {round(last['close'],2)}"
                )
            )

# ================= RESULT =================

def result():

    for sym, t in trades.items():

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
                    f"STOCK: {sym}"
                )
            )

        elif last["high"] >= t["tgt"]:

            t["status"] = "WIN"

            asyncio.run(
                send(
                    f"🎯 TARGET HIT\n\n"
                    f"STOCK: {sym}"
                )
            )

# ================= REPORT =================

def report():

    if not trades:
        return "❌ NO TRADES TODAY"

    out = []

    for sym, t in trades.items():

        out.append(

f"""📊 STOCK: {sym}

📅 DATE: {t['date']}

📡 RADAR TIME: {t['radar']}

🚀 ENTRY TIME: {t['entry']}

💰 ENTRY PRICE: {round(t['entry_price'], 2)}

🛑 SL: {round(t['sl'], 2)}

🎯 TARGET: {round(t['tgt'], 2)}

📌 STATUS: {t['status']}

━━━━━━━━━━━━━━━"""

        )

    return "\n".join(out)

# ================= LOOP =================

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

                        entry()

                        result()

            time.sleep(5)

        except Exception as e:

            print("❌ LOOP:", e)

# ================= WEBSOCKET =================

def subscribe_dynamic(sws, tokens):

    batch_size = 50

    for i in range(0, len(tokens), batch_size):

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

        # ================= LIVE =================

        if text == "LIVE":

            msg = report()

            asyncio.run(send(msg))

        # ================= RADAR =================

        elif text == "RADAR":

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

        # ================= STOP =================

        elif text == "STOP":

            scan_running = False

            asyncio.run(
                send(
                    "🛑 STOP COMMAND RECEIVED"
                )
            )

        # ================= STATUS =================

        elif text == "STATUS":

            if scan_running:

                msg = "📡 SCAN RUNNING"

            else:

                msg = "✅ IDLE"

            asyncio.run(send(msg))

        # ================= INVALID =================

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
