import time, datetime, pytz, asyncio, threading, os
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
    data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
    return obj, obj.getfeedToken()

angel, FEED_TOKEN = login()

# ================= TOKENS =================
TOKENS = {
    "RELIANCE": "2885",
    "SBIN": "3045",
    "TCS": "11536"
}

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
    df = df.copy()
    df["tp"] = (df["high"]+df["low"]+df["close"])/3
    df["cum_vol"] = df["volume"].cumsum()
    df["cum_pv"] = (df["tp"]*df["volume"]).cumsum()
    df["vwap"] = df["cum_pv"]/df["cum_vol"]
    return df

# ================= CANDLE BUILD =================
def update(symbol, price):
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

    # 15M
    t15 = now.replace(minute=(now.minute//15)*15, second=0, microsecond=0)
    candles_15m.setdefault(symbol, [])
    if not candles_15m[symbol] or candles_15m[symbol][-1]["time"]!=t15:
        candles_15m[symbol].append({"time":t15,"open":price,"high":price,"low":price,"close":price,"volume":1})
    else:
        c=candles_15m[symbol][-1]
        c["high"]=max(c["high"],price)
        c["low"]=min(c["low"],price)
        c["close"]=price
        c["volume"]+=1

    # 5M
    t5 = now.replace(minute=(now.minute//5)*5, second=0, microsecond=0)
    candles_5m.setdefault(symbol, [])
    if not candles_5m[symbol] or candles_5m[symbol][-1]["time"]!=t5:
        candles_5m[symbol].append({"time":t5,"open":price,"high":price,"low":price,"close":price,"volume":1})
    else:
        c=candles_5m[symbol][-1]
        c["high"]=max(c["high"],price)
        c["low"]=min(c["low"],price)
        c["close"]=price
        c["volume"]+=1

# ================= RADAR =================
def radar():
    for sym in candles_15m:
        df = pd.DataFrame(candles_15m[sym])
        if len(df)<5: continue

        df = vwap(df)
        last = df.iloc[-1]

        if last["close"]>last["vwap"] and last["close"]>last["open"]:
            active_radar[sym] = {
                "time": last["time"],
                "high": last["high"],
                "low": last["low"]
            }

# ================= ENTRY =================
def entry():
    now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

    if not (datetime.time(9,45)<=now.time()<=datetime.time(13,30)):
        return

    for sym in active_radar:

        if sym in trades: continue

        df = pd.DataFrame(candles_5m.get(sym,[]))
        if len(df)<10: continue

        df = vwap(df)
        last, prev = df.iloc[-1], df.iloc[-2]
        r = active_radar[sym]

        if last["close"]>last["vwap"] and prev["low"]<=prev["vwap"]*1.002:
            trades[sym] = {
                "date": now.strftime("%Y-%m-%d"),
                "radar": r["time"].strftime("%H:%M"),
                "entry": now.strftime("%H:%M"),
                "entry_price": last["close"],
                "sl": min(prev["low"], r["low"]),
                "tgt": last["close"]+(last["close"]-min(prev["low"], r["low"])),
                "status": "OPEN"
            }

# ================= RESULT =================
def result():
    for sym,t in trades.items():

        if t["status"]!="OPEN": continue

        df = pd.DataFrame(candles_5m.get(sym,[]))
        if len(df)<1: continue

        last=df.iloc[-1]

        if last["low"]<=t["sl"]:
            t["status"]="LOSS"
        elif last["high"]>=t["tgt"]:
            t["status"]="WIN"

# ================= REPORT =================
def report():
    out=[]
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

# ================= BACKTEST =================
def backtest(df15, df5, symbol, date):

    df15 = vwap(df15)
    df5 = vwap(df5)

    active = None
    trade = None

    for i in range(len(df15)):
        row15 = df15.iloc[i]

        # radar
        if row15["close"]>row15["vwap"] and row15["close"]>row15["open"]:
            active = row15
            trade = None

        # entry
        if active and not trade:
            for j in range(len(df5)):
                row5 = df5.iloc[j]

                if row5["time"]<=active["time"]:
                    continue

                if not(datetime.time(9,45)<=row5["time"].time()<=datetime.time(13,30)):
                    continue

                if row5["close"]>row5["vwap"] and row5["low"]<=row5["vwap"]*1.002:
                    entry=row5["close"]
                    sl=min(row5["low"],active["low"])
                    tgt=entry+(entry-sl)

                    trade={
                        "DATE":date,
                        "STOCK":symbol,
                        "RADAR":active["time"].strftime("%H:%M"),
                        "ENTRY":row5["time"].strftime("%H:%M"),
                        "ENTRY PRICE":round(entry,2),
                        "SL":round(sl,2),
                        "TGT":round(tgt,2),
                        "RESULT":"OPEN"
                    }

                    break

        # result
        if trade and trade["RESULT"]=="OPEN":
            for j in range(len(df5)):
                row5=df5.iloc[j]

                if row5["time"]<=pd.to_datetime(trade["ENTRY"]):
                    continue

                if row5["low"]<=trade["SL"]:
                    trade["RESULT"]="LOSS"
                    break
                elif row5["high"]>=trade["TGT"]:
                    trade["RESULT"]="WIN"
                    break

    return trade
# ================= LOOP =================
def loop():
    last=None
    ist=pytz.timezone("Asia/Kolkata")

    while True:
        now=datetime.datetime.now(ist)

        if datetime.time(9,15)<=now.time()<=datetime.time(15,30):

            if now.minute%15==1:
                key=now.strftime("%H:%M")
                if key!=last:
                    last=key
                    radar()

            entry()
            result()

        time.sleep(5)

# ================= SOCKET =================
def socket():
    sws=SmartWebSocketV2(API_KEY,CLIENT_ID,FEED_TOKEN)

    token_list=[{"exchangeType":1,"tokens":list(TOKENS.values())}]

    def on_data(ws,msg):
        token=msg.get("token")
        price=msg.get("last_traded_price",0)/100

        for sym,tok in TOKENS.items():
            if tok==token:
                update(sym,price)

    def on_open(ws):
        sws.subscribe(token_list)

    sws.on_open=on_open
    sws.on_data=on_data
    sws.connect()

# ================= TELEGRAM =================
@app.route("/",methods=["POST"])
def webhook():
    text=request.json["message"]["text"]

    if text=="LIVE":
        msg=report()
    elif text=="LIVE RADAR":
        msg=str(active_radar)
    else:
        msg="INVALID"

    asyncio.run(send(msg))
    return "ok"

# ================= MAIN =================
if __name__=="__main__":
    threading.Thread(target=socket,daemon=True).start()
    threading.Thread(target=loop,daemon=True).start()

    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
