import os
import re
import time
import requests
import pandas as pd
import yfinance as yf

from flask import Flask, request
from datetime import datetime

BOT_TOKEN = "8695080537:AAFolODguF8s1z88s_57HTVModIrmGojlno"
RENDER_URL = "https://vwap-bot-ia6r.onrender.com"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

LAST_REQUEST = {}

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

def is_duplicate(chat_id, text):
    key = f"{chat_id}:{text}"
    now = time.time()

    if key in LAST_REQUEST and now - LAST_REQUEST[key] < 5:
        return True

    LAST_REQUEST[key] = now
    return False


# ================= DATA =================

def get_data(symbol, interval):
    try:
        df = yf.download(symbol, interval=interval, period="30d", progress=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df if not df.empty else None

    except:
        return None


def to_ist(df):
    if df is None:
        return None

    df = df.copy()
    df.index = pd.to_datetime(df.index)

    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df.index = df.index.tz_convert("Asia/Kolkata")
    except:
        pass

    return df


def session_filter(df):
    try:
        return df.between_time("09:45", "13:30")
    except:
        return None


def filter_date(df, date):
    d = pd.to_datetime(date).date()
    return df[df.index.date == d]


def calculate_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()


# ================= STRATEGY =================

def find_15m_radars(df):
    df["VWAP"] = calculate_vwap(df)
    df["VOL_SMA20"] = df["Volume"].rolling(20).mean()

    radars = []

    for i in range(19, len(df)):
        r = df.iloc[i]

        if (
            r["Close"] > r["VWAP"]
            and r["Volume"] > 2 * r["VOL_SMA20"]
            and r["Close"] > r["Open"]
        ):
            radars.append({"time": df.index[i] + pd.Timedelta(minutes=15)})

    return radars


def find_5m_trade(df, radar_time):
    df = df[df.index > radar_time].copy()
    if df.empty:
        return None

    df["VWAP"] = calculate_vwap(df)

    for i in range(1, len(df)):
        r = df.iloc[i]
        prev = df.iloc[i - 1]

        score = 0

        if r["Close"] > r["VWAP"]:
            score += 1
        if r["Close"] > prev["High"]:
            score += 1
        if r["Volume"] > prev["Volume"]:
            score += 1
        if r["Low"] <= r["VWAP"]:
            score += 1

        if score < 3:
            continue

        entry = round(r["High"], 2)
        sl = round(prev["VWAP"], 2)
        target = round(entry + (entry - sl) * 2, 2)

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
            "score": score
        }

    return None


def scan_stock(symbol, date):
    df15 = session_filter(to_ist(get_data(symbol, "15m")))
    df5 = to_ist(get_data(symbol, "5m"))

    if df15 is None:
        return None

    radars = find_15m_radars(df15)

    for r in radars:
        if r["time"].date() != pd.to_datetime(date).date():
            continue

        trade = None
        if df5 is not None:
            temp5 = filter_date(df5, date)
            if not temp5.empty:
                trade = find_5m_trade(temp5, r["time"])

        return {"symbol": symbol, "radar": r, "trade": trade}

    return None


# ================= FORMAT =================

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


# ================= TELEGRAM =================

def send(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})
    except:
        pass


# ================= WEBHOOK =================

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

    try:

        # STOCK DATE
        if re.fullmatch(r"[A-Z]+ \d{4}-\d{2}-\d{2}", text):
            sym, date = text.split()
            symbol = sym + ".NS"

            send(chat_id, f"🔍 {sym} {date}")

            res = scan_stock(symbol, date)

            if res:
                send(chat_id, format_result(res))
            else:
                send(chat_id, "❌ No setup found")

            return "ok"

        # DATE SCAN ALL
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            send(chat_id, "📊 SCANNING ALL STOCKS...")

            found = False

            for s in FNO_STOCKS:
                res = scan_stock(s, text)
                if res:
                    send(chat_id, format_result(res))
                    found = True

            if not found:
                send(chat_id, "❌ No setups")

            return "ok"

        send(chat_id, "❌ Invalid Command")

    except Exception as e:
        send(chat_id, f"ERROR: {str(e)}")

    return "ok"


@app.route("/")
def home():
    return "BOT RUNNING"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
