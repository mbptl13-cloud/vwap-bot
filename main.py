import time, datetime, pytz, asyncio, threading, os, json, requests
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
FEED_TOKEN = None

# ================= SAFE REQUEST =================
def safe_json(session, url, headers, retries=3):
    for i in range(retries):
        try:
            r = session.get(url, headers=headers, timeout=10)

            if r.status_code != 200:
                print("❌ HTTP:", r.status_code)
                time.sleep(1)
                continue

            text = r.text.strip()

            if not text or text.startswith("<"):
                print("❌ Blocked/HTML response")
                time.sleep(1)
                continue

            return r.json()

        except Exception as e:
            print("❌ JSON error:", e)
            time.sleep(1)

    return None


# ================= LOGIN =================
def login():
    print("🔐 Logging in...")

    obj = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()

    data = obj.generateSession(CLIENT_ID, PASSWORD, totp)

    print("LOGIN RESPONSE:", data)

    feed = data["data"]["feedToken"]
    jwt = data["data"]["jwtToken"]

    return obj, feed, jwt


# ================= NSE TOKEN FETCH =================
def get_fno_tokens():
    print("🔄 Fetching FNO + Tokens (STABLE MODE)...")

    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        data = requests.get(url, headers=headers, timeout=20).json()
    except Exception as e:
        print("❌ Token master failed:", e)
        return {}

    tokens = {}

    for i in data:
        try:
            if i.get("exch_seg") == "NSE" and i.get("symbol", "").endswith("-EQ"):
                name = i["symbol"].replace("-EQ", "")
                tokens[name] = i["token"]
        except:
            continue

    print(f"✅ Tokens Loaded: {len(tokens)}")
    return tokens

# ================= REFRESH TOKENS =================
def refresh_tokens():
    global TOKENS
    ist = pytz.timezone("Asia/Kolkata")

    while True:
        now = datetime.datetime.now(ist)

        if now.hour == 8 and now.minute == 45:
            TOKENS = get_fno_tokens()
            print("🔁 TOKENS UPDATED")
            time.sleep(60)

        time.sleep(20)


# ================= STORAGE =================
candles_15m = {}
candles_5m = {}
active_radar = {}
trades = {}


# ================= TELEGRAM =================
async def send(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except:
        pass


# ================= VWAP =================
def vwap(df):
    df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
    df["cv"] = df["volume"].cumsum()
    df["cpv"] = (df["tp"] * df["volume"]).cumsum()
    df["vwap"] = df["cpv"] / df["cv"]
    return df


# ================= CANDLE UPDATE =================
def update(symbol, price):
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

    t15 = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    t5 = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)

    for tf, store, t in [(15, candles_15m, t15), (5, candles_5m, t5)]:
        store.setdefault(symbol, [])

        if not store[symbol] or store[symbol][-1]["time"] != t:
            store[symbol].append({
                "time": t,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 1
            })
        else:
            c = store[symbol][-1]
            c["high"] = max(c["high"], price)
            c["low"] = min(c["low"], price)
            c["close"] = price
            c["volume"] += 1


# ================= RADAR =================
def radar():
    for sym in candles_15m:
        df = pd.DataFrame(candles_15m.get(sym, []))
        if len(df) < 5:
            continue

        df = vwap(df)
        last = df.iloc[-1]

        if last["close"] > last["vwap"] and last["close"] > last["open"]:
            active_radar[sym] = {
                "time": last["time"],
                "high": last["high"],
                "low": last["low"]
            }


# ================= ENTRY =================
def entry():
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

    if not (datetime.time(9, 45) <= now.time() <= datetime.time(13, 30)):
        return

    for sym in active_radar:
        if sym in trades:
            continue

        df = pd.DataFrame(candles_5m.get(sym, []))
        if len(df) < 10:
            continue

        df = vwap(df)
        last, prev = df.iloc[-1], df.iloc[-2]
        r = active_radar[sym]

        if last["close"] > last["vwap"]:
            trades[sym] = {
                "date": now.strftime("%Y-%m-%d"),
                "radar": r["time"].strftime("%H:%M"),
                "entry": now.strftime("%H:%M"),
                "entry_price": last["close"],
                "sl": prev["low"],
                "tgt": last["close"] + (last["close"] - prev["low"]),
                "status": "OPEN"
            }


# ================= RESULT =================
def result():
    for sym, t in trades.items():
        if t["status"] != "OPEN":
            continue

        df = pd.DataFrame(candles_5m.get(sym, []))
        if len(df) < 1:
            continue

        last = df.iloc[-1]

        if last["low"] <= t["sl"]:
            t["status"] = "LOSS"
        elif last["high"] >= t["tgt"]:
            t["status"] = "WIN"


# ================= LOOP =================
def loop():
    ist = pytz.timezone("Asia/Kolkata")
    last = None

    while True:
        now = datetime.datetime.now(ist)

        if datetime.time(9, 15) <= now.time() <= datetime.time(15, 30):

            if now.minute % 15 == 1:
                key = now.strftime("%H:%M")
                if key != last:
                    last = key
                    radar()

            entry()
            result()

        time.sleep(3)


# ================= SOCKET =================
def socket():
    global FEED_TOKEN, JWT

    batch_size = 75  # IMPORTANT FIX (reduce load)

    while True:
        try:
            sws = SmartWebSocketV2(API_KEY, CLIENT_ID, FEED_TOKEN, JWT)

            tokens = list(TOKENS.values())

            def on_open(ws):
                print("🔌 Connected")

                for i in range(0, len(tokens), batch_size):
                    batch = tokens[i:i+batch_size]

                    sws.subscribe([
                        {"exchangeType": 1, "tokens": batch}
                    ])

                    time.sleep(0.3)  # IMPORTANT throttle

            def on_data(ws, msg):
                try:
                    token = msg.get("token")
                    price = msg.get("last_traded_price", 0) / 100

                    for sym, tok in TOKENS.items():
                        if tok == token:
                            update(sym, price)
                except:
                    pass

            def on_error(ws, error):
                print("❌ WS Error:", error)

            def on_close(ws):
                print("⚠️ WS Closed → reconnecting...")

            sws.on_open = on_open
            sws.on_data = on_data
            sws.on_error = on_error
            sws.on_close = on_close

            sws.connect()

        except Exception as e:
            print("❌ Socket crashed → retry in 5 sec:", e)
            time.sleep(5)

# ================= TELEGRAM WEBHOOK =================
@app.route("/", methods=["GET"])
def home():
    return "BOT RUNNING", 200

    if text == "LIVE":
        msg = str(trades)
    elif text == "RADAR":
        msg = str(active_radar)
    else:
        msg = "INVALID"

    asyncio.run(send(msg))
    return "ok"


# ================= MAIN =================
if __name__ == "__main__":

    print("🚀 BOT STARTING...")

    try:
        angel, FEED_TOKEN, JWT = login()
        print("✅ LOGIN SUCCESS")

        TOKENS = get_fno_tokens()

        threading.Thread(target=socket, daemon=True).start()
        threading.Thread(target=loop, daemon=True).start()
        threading.Thread(target=refresh_tokens, daemon=True).start()

        print("🔌 SYSTEM RUNNING")

        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

    except Exception as e:
        print("❌ CRASH:", e)
