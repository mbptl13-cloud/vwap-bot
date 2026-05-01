import os
import re
import time
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request
from datetime import datetime

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

LAST_REQUEST = {}

def is_duplicate(chat_id, text):
    key = f"{chat_id}:{text}"
    now = time.time()
    if key in LAST_REQUEST and now - LAST_REQUEST[key] < 5:
        return True
    LAST_REQUEST[key] = now
    return False


FNO_STOCKS = [
    "360ONE.NS",
    "ABB.NS",
    "APLAPOLLO.NS",
    "AUBANK.NS",
    "ADANIENSOL.NS",
    "ADANIENT.NS",
    "ADANIGREEN.NS",
    "ADANIPORTS.NS",
    "ADANIPOWER.NS",
    "ABCAPITAL.NS",
    "ALKEM.NS",
    "AMBER.NS",
    "AMBUJACEM.NS",
    "ANGELONE.NS",
    "APOLLOHOSP.NS",
    "ASHOKLEY.NS",
    "ASIANPAINT.NS",
    "ASTRAL.NS",
    "AUROPHARMA.NS",
    "DMART.NS",
    "AXISBANK.NS",
    "BSE.NS",
    "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "BAJAJHLDNG.NS",
    "BANDHANBNK.NS",
    "BANKBARODA.NS",
    "BANKINDIA.NS",
    "BDL.NS",
    "BEL.NS",
    "BHARATFORG.NS",
    "BHEL.NS",
    "BPCL.NS",
    "BHARTIARTL.NS",
    "BIOCON.NS",
    "BLUESTARCO.NS",
    "BOSCHLTD.NS",
    "BRITANNIA.NS",
    "CGPOWER.NS",
    "CANBK.NS",
    "CDSL.NS",
    "CHOLAFIN.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "COCHINSHIP.NS",
    "COFORGE.NS",
    "COLPAL.NS",
    "CAMS.NS",
    "CONCOR.NS",
    "CROMPTON.NS",
    "CUMMINSIND.NS",
    "DLF.NS",
    "DABUR.NS",
    "DALBHARAT.NS",
    "DELHIVERY.NS",
    "DIVISLAB.NS",
    "DIXON.NS",
    "DRREDDY.NS",
    "ETERNAL.NS",
    "EICHERMOT.NS",
    "EXIDEIND.NS",
    "FORCEMOT.NS",
    "NYKAA.NS",
    "FORTIS.NS",
    "GAIL.NS",
    "GMRAIRPORT.NS",
    "GLENMARK.NS",
    "GODFRYPHLP.NS",
    "GODREJCP.NS",
    "GODREJPROP.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCAMC.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HAVELLS.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HAL.NS",
    "HINDPETRO.NS",
    "HINDUNILVR.NS",
    "HINDZINC.NS",
    "POWERINDIA.NS",
    "HUDCO.NS",
    "HYUNDAI.NS",
    "ICICIBANK.NS",
    "ICICIGI.NS",
    "ICICIPRULI.NS",
    "IDFCFIRSTB.NS",
    "ITC.NS",
    "INDIANB.NS",
    "IEX.NS",
    "IOC.NS",
    "IRFC.NS",
    "IREDA.NS",
    "INDUSTOWER.NS",
    "INDUSINDBK.NS",
    "NAUKRI.NS",
    "INFY.NS",
    "INOXWIND.NS",
    "INDIGO.NS",
    "JINDALSTEL.NS",
    "JSWENERGY.NS",
    "JSWSTEEL.NS",
    "JIOFIN.NS",
    "JUBLFOOD.NS",
    "KEI.NS",
    "KPITTECH.NS",
    "KALYANKJIL.NS",
    "KAYNES.NS",
    "KFINTECH.NS",
    "KOTAKBANK.NS",
    "LTF.NS",
    "LICHSGFIN.NS",
    "LTM.NS",
    "LT.NS",
    "LAURUSLABS.NS",
    "LICI.NS",
    "LODHA.NS",
    "LUPIN.NS",
    "M&M.NS",
    "MANAPPURAM.NS",
    "MANKIND.NS",
    "MARICO.NS",
    "MARUTI.NS",
    "MFSL.NS",
    "MAXHEALTH.NS",
    "MAZDOCK.NS",
    "MOTILALOFS.NS",
    "MPHASIS.NS",
    "MCX.NS",
    "MUTHOOTFIN.NS",
    "NBCC.NS",
    "NHPC.NS",
    "NMDC.NS",
    "NTPC.NS",
    "NATIONALUM.NS",
    "NESTLEIND.NS",
    "NAM-INDIA.NS",
    "NUVAMA.NS",
    "OBEROIRLTY.NS",
    "ONGC.NS",
    "OIL.NS",
    "PAYTM.NS",
    "OFSS.NS",
    "POLICYBZR.NS",
    "PGEL.NS",
    "PIIND.NS",
    "PNBHOUSING.NS",
    "PAGEIND.NS",
    "PATANJALI.NS",
    "PERSISTENT.NS",
    "PETRONET.NS",
    "PIDILITIND.NS",
    "PPLPHARMA.NS",
    "POLYCAB.NS",
    "PFC.NS",
    "POWERGRID.NS",
    "PREMIERENE.NS",
    "PRESTIGE.NS",
    "PNB.NS",
    "RBLBANK.NS",
    "RECLTD.NS",
    "RVNL.NS",
    "RELIANCE.NS",
    "SBICARD.NS",
    "SBILIFE.NS",
    "SHREECEM.NS",
    "SRF.NS",
    "SAMMAANCAP.NS",
    "MOTHERSON.NS",
    "SHRIRAMFIN.NS",
    "SIEMENS.NS",
    "SOLARINDS.NS",
    "SONACOMS.NS",
    "SBIN.NS",
    "SAIL.NS",
    "SUNPHARMA.NS",
    "SUPREMEIND.NS",
    "SUZLON.NS",
    "SWIGGY.NS",
    "TATACONSUM.NS",
    "TVSMOTOR.NS",
    "TCS.NS",
    "TATAELXSI.NS",
    "TMPV.NS",
    "TATAPOWER.NS",
    "TATASTEEL.NS",
    "TATATECH.NS",
    "TECHM.NS",
    "FEDERALBNK.NS",
    "INDHOTEL.NS",
    "PHOENIXLTD.NS",
    "TITAN.NS",
    "TORNTPHARM.NS",
    "TORNTPOWER.NS",
    "TRENT.NS",
    "TIINDIA.NS",
    "UNOMINDA.NS",
    "UPL.NS",
    "ULTRACEMCO.NS",
    "UNIONBANK.NS",
    "UNITDSPR.NS",
    "VBL.NS",
    "VEDL.NS",
    "VMM.NS",
    "IDEA.NS",
    "VOLTAS.NS",
    "WAAREEENER.NS",
    "WIPRO.NS",
    "YESBANK.NS",
    "ZYDUSLIFE.NS"
]


def send(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage",
                      json={"chat_id": chat_id, "text": text},
                      timeout=20)
    except Exception as e:
        print("Send Error:", e)


def set_webhook():
    try:
        requests.get(f"{BASE_URL}/setWebhook?url={RENDER_URL}/webhook")
    except Exception as e:
        print(e)


# ================= DATA =================

def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="30d", progress=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df[["Open","High","Low","Close","Volume"]].dropna()


def to_ist(df):
    if df is None: return None
    df.index = pd.to_datetime(df.index)
    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("Asia/Kolkata")
    except: pass
    return df


def session_filter(df):
    try:
        df = df.between_time("09:45","13:30")
        return df if not df.empty else None
    except:
        return None


def filter_date(df, d):
    d = pd.to_datetime(d).date()
    df = df[df.index.date == d]
    return df if not df.empty else None


def vwap(df):
    tp = (df["High"]+df["Low"]+df["Close"])/3
    return (tp*df["Volume"]).cumsum()/df["Volume"].cumsum()


# ================= RADAR =================

def find_15m(df):
    df["VWAP"]=vwap(df)
    df["VOL_SMA"]=df["Volume"].rolling(20).mean()
    out=[]

    for i in range(19,len(df)):
        r=df.iloc[i]
        if pd.isna(r["VWAP"]) or pd.isna(r["VOL_SMA"]): continue

        if (
            r["Close"]>r["VWAP"]
            and r["Volume"]>500000
            and r["Volume"]>2*r["VOL_SMA"]
            and (r["Close"]-r["Open"])/r["Open"]>0.006
        ):
            out.append({"time":df.index[i]+pd.Timedelta(minutes=15)})
    return out


# ================= TRADE =================

def find_5m(df, radar_time):
    df=df[df.index>radar_time].copy()
    if df.empty: return None

    df["VWAP"]=vwap(df)

    for i in range(1,len(df)):
        r=df.iloc[i]
        p=df.iloc[i-1]

        t=r.name.time()
        if not (pd.to_datetime("09:45").time()<=t<=pd.to_datetime("13:30").time()):
            continue

        score=0
        if r["Low"]<=r["VWAP"]*1.002 and r["Close"]>r["VWAP"]: score+=1
        if r["Close"]>p["High"]: score+=1
        if r["Close"]>r["Open"]: score+=1
        if r["Volume"]>p["Volume"]*1.2: score+=1

        if score<4: continue

        entry=round(r["High"],2)
        sl=round(p["VWAP"],2)

        risk=entry-sl
        if risk<=0: continue

        if not (0.003<=risk/entry<=0.012): continue

        tgt=round(entry+risk*2,2)

        result="OPEN"
        for j in range(i+1,len(df)):
            nxt=df.iloc[j]
            if nxt.name.time()>pd.to_datetime("15:30").time(): break
            if nxt["Low"]<=sl: result="LOSS"; break
            if nxt["High"]>=tgt: result="WIN"; break

        return {
            "time":df.index[i]+pd.Timedelta(minutes=5),
            "entry":entry,"sl":sl,"target":tgt,
            "result":result,"score":f"{score}/5"
        }
    return None


# ================= SCAN =================

def scan_stock(sym,date=None):
    df15=to_ist(get_data(sym,"15m"))
    df5=to_ist(get_data(sym,"5m"))

    if df15 is None: return None
    df15=session_filter(df15)
    if df15 is None: return None

    radars=find_15m(df15)
    if not radars: return None

    for r in radars:
        if date and r["time"].date()!=pd.to_datetime(date).date():
            continue

        trade=None
        if df5 is not None:
            d=filter_date(df5,r["time"].strftime("%Y-%m-%d"))
            if d is not None:
                trade=find_5m(d,r["time"])

        return {"symbol":sym,"radar":r,"trade":trade}
    return None


def scan_all(date=None):
    res=[]
    for s in FNO_STOCKS:
        r=scan_stock(s,date)
        if r: res.append(r)
    return res


def run_range(sym,d1,d2):
    out=[]
    for d in pd.date_range(d1,d2):
        r=scan_stock(sym,str(d.date()))
        if r: out.append(r)
    return out


# ================= FORMAT =================

def fmt(r):
    msg=f"📊 {r['symbol']}\n"
    msg+=f"15M: {r['radar']['time'].strftime('%Y-%m-%d %H:%M')}\n"

    if r["trade"]:
        t=r["trade"]
        msg+=f"5M: {t['time'].strftime('%Y-%m-%d %H:%M')}\n"
        msg+=f"Score: {t['score']}\n"
        msg+=f"Entry: {t['entry']} SL: {t['sl']} TG: {t['target']}\n"
        msg+=f"Result: {t['result']}"
    else:
        msg+="5M: NO SETUP"

    return msg


# ================= WEBHOOK =================

@app.route("/webhook",methods=["POST"])
def webhook():
    data=request.get_json(force=True)
    if "message" not in data: return "ok"

    msg=data["message"]
    chat_id=msg["chat"]["id"]
    text=msg.get("text","").strip().upper()

    if is_duplicate(chat_id,text): return "ok"

    today=datetime.now().strftime("%Y-%m-%d")

    # LIVE
    if text=="LIVE":
        send(chat_id,"📡 LIVE SCAN")
        for r in scan_all(today):
            send(chat_id,fmt(r))
        return "ok"

    # RADAR LIVE
    if text=="RADAR LIVE":
        send(chat_id,"📡 RADAR LIVE")
        for s in FNO_STOCKS:
            r=scan_stock(s,today)
            if r:
                send(chat_id,f"{s} → {r['radar']['time'].strftime('%H:%M')}")
        return "ok"

    # DATE RADAR
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} RADAR",text):
        d=text.split()[0]
        for s in FNO_STOCKS:
            r=scan_stock(s,d)
            if r:
                send(chat_id,f"{s} → {r['radar']['time'].strftime('%H:%M')}")
        return "ok"

    # DATE SCAN
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}",text):
        for r in scan_all(text):
            send(chat_id,fmt(r))
        return "ok"

    # RANGE
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2} TO \d{4}-\d{2}-\d{2}",text):
        sym,d1,_,d2=text.split()
        for r in run_range(sym+".NS",d1,d2):
            send(chat_id,fmt(r))
        return "ok"

    # SINGLE STOCK
    if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}",text):
        sym,d=text.split()
        r=scan_stock(sym+".NS",d)
        if r: send(chat_id,fmt(r))
        else: send(chat_id,"No setup")
        return "ok"

    send(chat_id,"Command OK")
    return "ok"


@app.route("/")
def home():
    return "BOT RUNNING"


if __name__=="__main__":
    set_webhook()
    app.run(host="0.0.0.0",port=PORT)
