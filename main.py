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
IST = pytz.timezone("Asia/Kolkata")

TOKENS = {}
TOKEN_MAP = {}

FEED_TOKEN = None
JWT = None
angel = None

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

    if not data["status"]:
        raise Exception("LOGIN FAILED")

    feed = data["data"]["feedToken"]
    jwt = data["data"]["jwtToken"]

    print("✅ LOGIN SUCCESS")

    return obj, feed, jwt


# ================= TOKEN FETCH =================
def get_fno_tokens():

    print("🔄 Fetching Tokens...")

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
                tok = str(i["token"])

                tokens[sym] = tok
                token_map[tok] = sym

        except:
            pass

    print(f"✅ Tokens Loaded: {len(tokens)}")

    return tokens, token_map


# ================= VWAP =================
def vwap(df):

    df = df.copy()

    df["tp"] = (
        df["high"] +
        df["low"] +
        df["close"]
    ) / 3

    df["cv"] = df["volume"].cumsum()

    df["cpv"] = (
        df["tp"] * df["volume"]
    ).cumsum()

    df["vwap"] = df["cpv"] / df["cv"]

    return df


# ================= GET CANDLES =================
def get_candle_data(token, interval, days=5):

    try:

        now = datetime.datetime.now(IST)

        from_date = (
            now -
            datetime.timedelta(days=days)
        ).strftime("%Y-%m-%d 09:15")

        to_date = now.strftime("%Y-%m-%d %H:%M")

        params = {

            "exchange": "NSE",

            "symboltoken": token,

            "interval": interval,

            "fromdate": from_date,

            "todate": to_date
        }

        hist = angel.getCandleData(params)

        data = hist.get("data")

        if not data:
            return None

        df = pd.DataFrame(data, columns=[

            "time",
            "open",
            "high",
            "low",
            "close",
            "volume"

        ])

        for col in [

            "open",
            "high",
            "low",
            "close",
            "volume"

        ]:

            df[col] = df[col].astype(float)

        return df

    except Exception as e:

        print("❌ Candle API Error:", e)

        return None


# ================= RADAR =================
# ================= RADAR =================
def radar():

    try:

        active_radar.clear()

        count = 0

        print("📡 RUNNING RADAR...")

        for sym, token in list(TOKENS.items())[:100]:

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

                # ================= CONDITIONS =================

                volume_cond = (
                    last["volume"] > 500000
                )

                turnover_cond = (
                    (
                        last["close"] *
                        last["volume"]
                    ) > 15000000
                )

                range_percent = (
                    (
                        (
                            last["high"] -
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
                            last["close"] -
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
                    last["close"] >
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
                    last["close"] >
                    last["open"]
                )

                # ================= TELEGRAM DEBUG =================

                debug_msg = f"""
📊 {sym}

VOL = {round(last['volume'], 2)}
VOL_SMA20 = {round(last['vol_sma20'], 2)}

TURNOVER = {round(last['close'] * last['volume'], 2)}

RANGE% = {round(range_percent, 2)}
BODY% = {round(body_percent, 2)}

VWAP = {round(last['vwap'], 2)}
CLOSE = {round(last['close'], 2)}

volume_cond = {volume_cond}
turnover_cond = {turnover_cond}
range_cond = {range_cond}
body_cond = {body_cond}
vwap_cond = {vwap_cond}
volume_blast_cond = {volume_blast_cond}
bullish_cond = {bullish_cond}
"""

                asyncio.run(send(debug_msg))

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

                    print(f"📡 RADAR: {sym}")

                    asyncio.run(
                        send(f"📡 RADAR FOUND: {sym}")
                    )

            except Exception as e:

                print(f"❌ {sym} radar error:", e)

        print(f"✅ RADAR COUNT: {count}")

        asyncio.run(
            send(f"✅ RADAR SCAN DONE\nTOTAL RADAR = {count}")
        )

    except Exception as e:

        print("❌ RADAR ERROR:", e)

        asyncio.run(
            send(f"❌ RADAR ERROR:\n{e}")
        )


# ================= ENTRY =================
def entry():

    try:

        now = datetime.datetime.now(IST)

        if not (
            datetime.time(9, 30)
            <= now.time()
            <= datetime.time(14, 30)
        ):
            return

        for sym in list(active_radar.keys()):

            if sym in trades:
                continue

            token = TOKENS[sym]

            df = get_candle_data(
                token,
                "FIVE_MINUTE"
            )

            if df is None:
                continue

            if len(df) < 20:
                continue

            df = vwap(df)

            last = df.iloc[-1]
            prev = df.iloc[-2]

            # ================= VWAP PULLBACK =================

            touch_vwap = (

                last["low"]
                <=
                last["vwap"] * 1.002

            )

            bullish_candle = (
                last["close"] >
                last["open"]
            )

            close_above_vwap = (
                last["close"] >
                last["vwap"]
            )

            breakout = (
                last["close"] >
                prev["high"]
            )

            # ================= FINAL ENTRY =================

            if (

                touch_vwap
                and
                bullish_candle
                and
                close_above_vwap
                and
                breakout

            ):

                sl = min(
                    last["low"],
                    prev["low"]
                )

                target = (

                    last["close"]

                    +

                    (
                        (
                            last["close"] -
                            sl
                        ) * 2
                    )

                )

                trades[sym] = {

                    "date":
                        now.strftime("%Y-%m-%d"),

                    "radar":
                        active_radar[sym]["time"],

                    "entry":
                        now.strftime("%H:%M"),

                    "entry_price":
                        last["close"],

                    "sl":
                        sl,

                    "tgt":
                        target,

                    "status":
                        "OPEN"

                }

                print(f"🚀 ENTRY: {sym}")

    except Exception as e:

        print("❌ ENTRY ERROR:", e)


# ================= RESULT =================
def result():

    try:

        for sym, t in trades.items():

            if t["status"] != "OPEN":
                continue

            ltp = live_price.get(sym)

            if not ltp:
                continue

            if ltp <= t["sl"]:

                t["status"] = "LOSS"

                print(f"❌ SL HIT: {sym}")

            elif ltp >= t["tgt"]:

                t["status"] = "WIN"

                print(f"✅ TARGET HIT: {sym}")

    except Exception as e:

        print("❌ RESULT ERROR:", e)


# ================= REPORT =================
def report():

    if not trades:
        return "❌ NO TRADES TODAY"

    out = []

    for sym, t in trades.items():

        out.append(

f"""📊 STOCK: {sym}

📅 DATE: {t['date']}

📡 RADAR: {t['radar']}

🚀 ENTRY: {t['entry']}

💰 ENTRY PRICE: {round(t['entry_price'], 2)}

🛑 SL: {round(t['sl'], 2)}

🎯 TARGET: {round(t['tgt'], 2)}

📌 STATUS: {t['status']}

----------------------"""

        )

    return "\n".join(out)


# ================= LOOP =================
def loop():

    last_radar = None
    last_entry = None

    while True:

        try:

            now = datetime.datetime.now(IST)

            if (
                datetime.time(9, 15)
                <= now.time()
                <= datetime.time(15, 30)
            ):

                radar_key = now.strftime(
                    "%Y-%m-%d %H:%M"
                )

                # ================= RADAR =================
                if now.minute % 15 == 1:

                    if radar_key != last_radar:

                        last_radar = radar_key

                        radar()

                # ================= ENTRY =================
                if now.minute % 5 == 0:

                    if radar_key != last_entry:

                        last_entry = radar_key

                        entry()

                result()

            time.sleep(5)

        except Exception as e:

            print("❌ LOOP ERROR:", e)

            time.sleep(5)


# ================= SOCKET =================
def socket():

    global FEED_TOKEN
    global JWT

    while True:

        try:

            print("🔌 STARTING WEBSOCKET...")

            sws = SmartWebSocketV2(
                AUTH_TOKEN=JWT,
                API_KEY=API_KEY,
                CLIENT_CODE=CLIENT_ID,
                FEED_TOKEN=FEED_TOKEN
            )

            # ================= OPEN =================
            def on_open(ws):

                print("✅ SOCKET CONNECTED")

                tokens = list(TOKENS.values())[:500]

                batch_size = 50

                for i in range(
                    0,
                    len(tokens),
                    batch_size
                ):

                    batch = tokens[i:i+batch_size]

                    sws.subscribe(

                        correlation_id=f"sub_{i}",

                        mode=1,

                        token_list=[

                            {
                                "exchangeType": 1,
                                "tokens": batch
                            }

                        ]
                    )

                    time.sleep(1)

            # ================= DATA =================
            def on_data(ws, msg):

                try:

                    token = str(
                        msg.get("token")
                    )

                    ltp = float(
                        msg.get(
                            "last_traded_price",
                            0
                        )
                    ) / 100

                    symbol = TOKEN_MAP.get(token)

                    if symbol:

                        live_price[symbol] = ltp

                except:
                    pass

            # ================= ERROR =================
            def on_error(ws, e):
                print("❌ SOCKET ERROR:", e)

            # ================= CLOSE =================
            def on_close(ws):
                print("⚠ SOCKET CLOSED")

            sws.on_open = on_open
            sws.on_data = on_data
            sws.on_error = on_error
            sws.on_close = on_close

            sws.connect()

        except Exception as e:

            print("❌ SOCKET RESTART:", e)

            time.sleep(10)


# ================= TELEGRAM =================
async def send(msg):

    try:

        await bot.send_message(
            chat_id=CHAT_ID,
            text=msg
        )

    except Exception as e:

        print("❌ TELEGRAM ERROR:", e)


# ================= WEBHOOK =================
@app.route("/", methods=["POST"])
def webhook():

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

        # ================= RADAR =================
        elif text == "RADAR":

            radar()

            if not active_radar:

                msg = "❌ NO RADAR FOUND"

            else:

                msg = "\n".join(

                    [
                        f"📡 {x}"
                        for x in active_radar.keys()
                    ]

                )

        else:

            msg = (
                "AVAILABLE COMMANDS:\n\n"
                "LIVE\n"
                "RADAR"
            )

        asyncio.run(send(msg))

        return "ok", 200

    except Exception as e:

        print("❌ WEBHOOK ERROR:", e)

        return "error", 200


# ================= HEALTH =================
@app.route("/", methods=["GET"])
def home():
    return "BOT RUNNING", 200


# ================= MAIN =================
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

        print("🔌 SYSTEM RUNNING")

        port = int(
            os.environ.get("PORT", 10000)
        )

        app.run(
            host="0.0.0.0",
            port=port
        )

    except Exception as e:

        print("❌ MAIN CRASH:", e)
