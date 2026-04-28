import pandas as pd
import numpy as np
import yfinance as yf
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8689896067:AAEuHnXG8f7orhfygCKvHoDItQmJTqzGGB4"

DEFAULT_STOCKS = [
    "360ONE.NS","ABB.NS","APLAPOLLO.NS","AUBANK.NS","ADANIENT.NS",
    "ADANIGREEN.NS","ADANIPORTS.NS","ADANIPOWER.NS","AXISBANK.NS",
    "BAJFINANCE.NS","BEL.NS","BHEL.NS","BPCL.NS","BHARTIARTL.NS",
    "CIPLA.NS","COALINDIA.NS","DLF.NS","DRREDDY.NS","EICHERMOT.NS",
    "HDFCBANK.NS","ICICIBANK.NS","INFY.NS","ITC.NS","KOTAKBANK.NS",
    "LT.NS","MARUTI.NS","M&M.NS","NESTLEIND.NS","NTPC.NS",
    "ONGC.NS","POWERGRID.NS","RELIANCE.NS","SBIN.NS","SUNPHARMA.NS",
    "TATAMOTORS.NS","TATASTEEL.NS","TCS.NS","TECHM.NS","WIPRO.NS"
]

# =========================
# HELPERS
# =========================

def safe_float(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except:
        return None


def calculate_vwap(df):
    df = df.copy()
    df["VWAP"] = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()
    return df

# =========================
# DATA
# =========================

def get_data(stock, interval, start, end):
    df = yf.download(stock, interval=interval, start=start, end=end, progress=False)
    df.dropna(inplace=True)
    return df

# =========================
# 15M RADAR (INSTITUTIONAL FILTER)
# =========================

def radar_15m(df15):
    if df15.empty or len(df15) < 20:
        return False, None

    df15 = calculate_vwap(df15)
    df15["vol_sma_20"] = df15["Volume"].rolling(20).mean()

    valid_15m = []

    for idx, row in df15.iterrows():

        if idx.time() <= pd.to_datetime("09:30").time():
            continue

        o = safe_float(row["Open"])
        h = safe_float(row["High"])
        l = safe_float(row["Low"])
        c = safe_float(row["Close"])
        v = safe_float(row["Volume"])
        vwap = safe_float(row["VWAP"])
        vol_sma = safe_float(row["vol_sma_20"])

        if None in [o, h, l, c, v, vwap]:
            continue

        candle_range = h - l
        if candle_range <= 0:
            continue

        body = abs(c - o)

        cond1 = v > 500000
        cond2 = (c * v) > 150000000
        cond3 = (candle_range / o) * 100 > 1
        cond4 = (body / o) * 100 > 0.6
        cond5 = c > vwap
        cond6 = vol_sma is not None and v > (2 * vol_sma)
        cond7 = c > o

        if cond1 and cond2 and cond3 and cond4 and cond5 and cond6 and cond7:
            valid_15m.append(idx)

    if not valid_15m:
        return False, None

    return True, valid_15m[-1]

# =========================
# 5M ENTRY (VWAP PRICE ACTION)
# =========================

def entry_5m(df5):
    if df5.empty or len(df5) < 20:
        return False, None, None

    df5 = calculate_vwap(df5)

    for i in range(2, len(df5)):

        prev = df5.iloc[i-1]
        curr = df5.iloc[i]

        o = safe_float(curr["Open"])
        c = safe_float(curr["Close"])
        vwap = safe_float(curr["VWAP"])

        prev_c = safe_float(prev["Close"])
        prev_vwap = safe_float(prev["VWAP"])

        if None in [o, c, vwap, prev_c, prev_vwap]:
            continue

        cond1 = c > vwap
        cond2 = prev_c < prev_vwap
        cond3 = c > o

        if cond1 and cond2 and cond3:
            return True, df5.index[i], c

    return False, None, None

# =========================
# CORE ENGINE
# =========================

def find_trade(stock, df15, df5):

    result = {
        "stock": stock,
        "radar": "NO",
        "entry": "NO",
        "time_15m": None,
        "time_5m": None,
        "price": None
    }

    radar, t15 = radar_15m(df15)

    if not radar:
        return result

    result["radar"] = "YES"
    result["time_15m"] = str(t15)

    entry, t5, price = entry_5m(df5)

    if entry:
        result["entry"] = "YES"
        result["time_5m"] = str(t5)
        result["price"] = round(price, 2)

    return result

# =========================
# SCANNER
# =========================

def scan(date):
    results = []

    for stock in DEFAULT_STOCKS:
        try:
            df15 = get_data(stock, "15m", date, date)
            df5 = get_data(stock, "5m", date, date)

            if df15.empty or df5.empty:
                continue

            results.append(find_trade(stock, df15, df5))

        except Exception as e:
            print("Error:", stock, e)

    return results

# =========================
# MODES
# =========================

def live_scan():
    today = pd.Timestamp.today().date().isoformat()
    return scan(today)


def backtest(date):
    return scan(date)


def radar_only(date):
    data = scan(date)
    return [x for x in data if x["radar"] == "YES"]

# =========================
# TELEGRAM
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Radar Bot Ready\nCommands: /live /backtest /radar")


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Running Live Scan...")

    results = live_scan()

    for r in results:
        msg = f"""
📡 {r['stock']}
RADAR: {r['radar']}
ENTRY: {r['entry']}
15M: {r['time_15m']}
5M: {r['time_5m']}
PRICE: {r['price']}
"""
        await update.message.reply_text(msg)


async def backtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else None
    if not date:
        await update.message.reply_text("Send date like /backtest 2026-04-06")
        return

    results = backtest(date)
    await update.message.reply_text(str(results))


async def radar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.args[0] if context.args else None
    if not date:
        await update.message.reply_text("Send date like /radar 2026-04-06")
        return

    results = radar_only(date)
    await update.message.reply_text(str(results))

# =========================
# MAIN (RENDER SAFE)
# =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("backtest", backtest_cmd))
    app.add_handler(CommandHandler("radar", radar_cmd))

    print("Bot Running...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
    
