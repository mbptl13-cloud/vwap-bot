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

# ================= LOGIN =================
def login():
    obj = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj, obj.getfeedToken()

angel, FEED_TOKEN = login()

# ================= AUTO TOKEN FETCH =================
def get_fno_tokens():
    print("🔄 Fetching FNO + Tokens...")

    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)

    url = "https://www.nseindia.com/api/derivatives/equity-stockIndices"
    data = session.get(url, headers=headers).json()

    fno = set([x["symbol"] for x in data["data"]])

    url2 = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    inst = requests.get(url2).json()

    tokens = {}
    for i in inst:
        if i["exch_seg"] == "NSE" and i["symbol"].endswith("-EQ"):
            name = i["symbol"].replace("-EQ", "")
            if name in fno:
                tokens[name] = i["token"]

    print(f"✅ Tokens Loaded: {len(tokens)}")
    return tokens

TOKENS = get_fno_tokens()

# ================= DAILY REFRESH =================
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
    df["tp"] = (df["high"]+df["low"]+df["close"])/3
    df["cv"] = df["volume"].cumsum()
    df["cpv"] = (df["tp"]*df["volume"]).cumsum()
    df["vwap"] = df["cpv"]/df["cv"]
    return df

# ================= CANDLE =================
def update(symbol, price):
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

    t15 = now.replace(minute=(now.minute//15)*15, second=0, microsecond=0)
    t5 = now.replace(minute=(now.minute//5)*5, second=0, microsecond=0)

    for tf, store, t in [(15, candles_15m, t15),(5, candles_5m, t5)]:
        store.setdefault(symbol, [])
        if not store[symbol] or store[symbol][-1]["time"] != t:
            store[symbol].append({"time":t,"open":price,"high":price,"low":price,"close":price,"volume":1})
        else:
            c = store[symbol][-1]
            c["high"]=max(c["high"],price)
            c["low"]=min(c["low"],price)
            c["close"]=price
            c["volume"]+=1

# ================= BATCH SCAN =================
def process_batch(symbols):
    for sym in symbols:
        df = pd.DataFrame(candles_15m.get(sym, []))
        if len(df) < 5: continue

        df = vwap(df)
        last = df.iloc[-1]

        if last["close"] > last["vwap"] and last["close"] > last["open"]:
            active_radar[sym] = {
                "time": last["time"],
                "high": last["high"],
                "low": last["low"]
            }

# ================= RADAR =================
def radar():
    symbols = list(candles_15m.keys())
    batch_size = 20

    threads = []
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        t = threading.Thread(target=process_batch, args=(batch,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

# ================= ENTRY =================
def entry():
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

    if not (datetime.time(9,45)<=now.time()<=datetime.time(13,30)):
        return

    for sym in active_radar:
        if sym in trades: continue

        df = pd.DataFrame(candles_5m.get(sym, []))
        if len(df) < 10: continue

        df = vwap(df)
        last, prev = df.iloc[-1], df.iloc[-2]
        r = active_radar[sym]

        if last["close"] > last["vwap"] and prev["low"] <= prev["vwap"]*1.002:
            trades[sym] = {
                "date": now.strftime("%Y-%m-%d"),
                "radar": r["time"].strftime("%H:%M"),
                "entry": now.strftime("%H:%M"),
                "entry_price": last["close"],
                "sl": min(prev["low"], r["low"]),
                "tgt": last["close"] + (last["close"] - min(prev["low"], r["low"])),
                "status": "OPEN"
            }

# ================= RESULT =================
def result():
    for sym,t in trades.items():
        if t["status"] != "OPEN": continue

        df = pd.DataFrame(candles_5m.get(sym, []))
        if len(df) < 1: continue

        last = df.iloc[-1]

        if last["low"] <= t["sl"]:
            t["status"] = "LOSS"
        elif last["high"] >= t["tgt"]:
            t["status"] = "WIN"

# ================= REPORT =================
def report():
    out = []
    for sym,t in trades.items():
        out.append(f"""
DATE - {t['date']}
STOCK - {sym}
RADAR - {t['radar']}
ENTRY - {t['entry']}
ENTRY PRICE - {round(t['entry_price'],2)}
SL - {round(t['sl'],2)}
TGT - {round(t['tgt'],2)}
RESULT - {t['status']}
""")
    return "\n".join(out) if out else "NO DATA"

# ================= LOOP =================
def loop():
    last = None
    ist = pytz.timezone("Asia/Kolkata")

    while True:
        now = datetime.datetime.now(ist)

        if datetime.time(9,15)<=now.time()<=datetime.time(15,30):

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
    sws = SmartWebSocketV2(API_KEY, CLIENT_ID, FEED_TOKEN)

    tokens = list(TOKENS.values())
    batch_size = 50

    def on_open(ws):
        print("🔌 Connected")

        for i in range(0, len(tokens), batch_size):
            sub = [{"exchangeType":1, "tokens":tokens[i:i+batch_size]}]
            sws.subscribe(sub)
            time.sleep(0.5)

    def on_data(ws, msg):
        token = msg.get("token")
        price = msg.get("last_traded_price",0)/100

        for sym,tok in TOKENS.items():
            if tok == token:
                update(sym, price)

    sws.on_open = on_open
    sws.on_data = on_data
    sws.connect()

# ================= TELEGRAM =================
@app.route("/", methods=["POST"])
def webhook():
    text = request.json["message"]["text"]

    if text == "LIVE":
        msg = report()
    elif text == "LIVE RADAR":
        msg = str(active_radar)
    else:
        msg = "INVALID"

    asyncio.run(send(msg))
    return "ok"

# ================= MAIN =================
if __name__ == "__main__":
    print("🚀 START")

    threading.Thread(target=socket, daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()
    threading.Thread(target=refresh_tokens, daemon=True).start()

    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
