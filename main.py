# FULL FINAL HYBRID VWAP TELEGRAM BOT
# Commands:
# 1. LIVE
# 2. 2026-04-06
# 3. BHEL 2026-04-06
# 4. BHEL 2026-04-01 to 2026-04-20

# =========================
# INSTALL REQUIRED:
# pip install python-telegram-bot yfinance pandas requests
# =========================

import os
import asyncio
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================================================
# BOT TOKEN
# =========================================================

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

# Optional:
# BOT_TOKEN = "YOUR_BOT_TOKEN"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")


# =========================================================
# SAFE FLOAT FIX
# =========================================================

def safe_float(value):
    try:
        if hasattr(value, "iloc"):
            return float(value.iloc[0])
        return float(value)
    except:
        return None


# =========================================================
# HYBRID WATCHLIST SYSTEM
# NSE LIVE API + FULL BACKUP + FORCE ADD
# =========================================================

def get_fno_stocks():

    backup_stocks = [

        # BANKS
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "AXISBANK.NS",
        "KOTAKBANK.NS",
        "BANKBARODA.NS",
        "PNB.NS",
        "FEDERALBNK.NS",
        "INDUSINDBK.NS",

        # FINANCIALS
        "BAJFINANCE.NS",
        "BAJAJFINSV.NS",
        "PFC.NS",
        "RECLTD.NS",
        "CHOLAFIN.NS",
        "SHRIRAMFIN.NS",

        # IT
        "TCS.NS",
        "INFY.NS",
        "WIPRO.NS",
        "HCLTECH.NS",
        "TECHM.NS",
        "LTIM.NS",
        "COFORGE.NS",

        # AUTO
        "TATAMOTORS.NS",
        "MARUTI.NS",
        "M&M.NS",
        "HEROMOTOCO.NS",
        "EICHERMOT.NS",
        "ASHOKLEY.NS",

        # ENERGY
        "RELIANCE.NS",
        "ONGC.NS",
        "BPCL.NS",
        "IOC.NS",
        "GAIL.NS",

        # ADANI
        "ADANIENT.NS",
        "ADANIPORTS.NS",
        "ADANIGREEN.NS",
        "ADANIPOWER.NS",
        "ATGL.NS",

        # METALS
        "TATASTEEL.NS",
        "JSWSTEEL.NS",
        "HINDALCO.NS",
        "SAIL.NS",
        "VEDL.NS",

        # CAPITAL GOODS
        "LT.NS",
        "SIEMENS.NS",
        "ABB.NS",
        "BHEL.NS",
        "HAL.NS",
        "BEL.NS",
        "CGPOWER.NS",

        # PHARMA
        "SUNPHARMA.NS",
        "DRREDDY.NS",
        "CIPLA.NS",
        "DIVISLAB.NS",
        "LUPIN.NS",

        # FMCG
        "ITC.NS",
        "HINDUNILVR.NS",
        "NESTLEIND.NS",
        "BRITANNIA.NS",

        # REALTY
        "DLF.NS",
        "GODREJPROP.NS",

        # SPECIAL
        "TRENT.NS",
        "KAYNES.NS",
        "POLICYBZR.NS",
        "AMBER.NS",
        "INOXWIND.NS",
        "IRCTC.NS",
        "RVNL.NS",
        "IRFC.NS",
        "NHPC.NS",
        "SUZLON.NS",
        "ZOMATO.NS",
        "PAYTM.NS",
        "NYKAA.NS",
        "INDIGO.NS",
        "DMART.NS"
    ]

    try:
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.nseindia.com/"
        }

        session.get(
            "https://www.nseindia.com/",
            headers=headers,
            timeout=10
        )

        url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"

        response = session.get(
            url,
            headers=headers,
            timeout=10
        )

        data = response.json()

        live_stocks = []

        for item in data["data"]:
            symbol = item["symbol"].strip()

            if symbol:
                live_stocks.append(symbol + ".NS")

        print(f"NSE Live Loaded: {len(live_stocks)}")

    except Exception as e:
        print("NSE API Failed → Backup Used")
        print("Reason:", e)

        live_stocks = []

    final_watchlist = list(
        set(live_stocks + backup_stocks)
    )

    must_have = [
        "ADANIGREEN.NS",
        "ADANIPOWER.NS",
        "TRENT.NS",
        "KAYNES.NS",
        "POLICYBZR.NS",
        "AMBER.NS",
        "INOXWIND.NS",
        "HAL.NS",
        "PFC.NS",
        "SIEMENS.NS",
        "BHEL.NS",
        "BEL.NS",
        "ADANIENT.NS"
    ]

    for stock in must_have:
        if stock not in final_watchlist:
            final_watchlist.append(stock)

    final_watchlist = list(set(final_watchlist))
    final_watchlist.sort()

    print(f"FINAL WATCHLIST SIZE: {len(final_watchlist)}")

    return final_watchlist


WATCHLIST = get_fno_stocks()


# =========================================================
# VWAP
# =========================================================

def calculate_vwap(df):
    df = df.copy()

    df["cum_vol"] = df["Volume"].cumsum()
    df["cum_vol_price"] = (
        (df["Close"] * df["Volume"]).cumsum()
    )

    df["VWAP"] = (
        df["cum_vol_price"] / df["cum_vol"]
    )

    return df


# =========================================================
# MAIN STRATEGY
# =========================================================

def find_trade(stock, date):
    try:
        start = date
        end = pd.to_datetime(date) + pd.Timedelta(days=1)

        df15 = yf.download(
            stock,
            interval="15m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True
        )

        df5 = yf.download(
            stock,
            interval="5m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True
        )

        if len(df15) < 5 or len(df5) < 10:
            return None

        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert(
                "Asia/Kolkata"
            ).tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert(
                "Asia/Kolkata"
            ).tz_localize(None)

        df5 = calculate_vwap(df5)

        # =================================
        # 15m FILTER
        # =================================

        valid_15m = []

        avg_vol = safe_float(
            df15["Volume"].rolling(20).mean().iloc[-1]
        )

        for idx, row in df15.iterrows():

            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            open_p = safe_float(row["Open"])
            high_p = safe_float(row["High"])
            low_p = safe_float(row["Low"])
            close_p = safe_float(row["Close"])
            vol = safe_float(row["Volume"])

            if None in [open_p, high_p, low_p, close_p, vol]:
                continue

            candle_range = high_p - low_p
            body = abs(close_p - open_p)
            upper_wick = high_p - close_p

            if candle_range <= 0:
                continue

            cond1 = vol > 500000

            cond2 = (
                close_p * vol
            ) > 150000000

            range_percent = (
                (high_p - low_p)
                / open_p
            ) * 100

            cond3 = range_percent > 1

            body_percent = (
                body / open_p
            ) * 100

            cond4 = body_percent > 0.6

            cond5 = close_p > open_p

            cond6 = (
                avg_vol is not None
                and vol > avg_vol * 2
            )

            cond7 = (
                (upper_wick / candle_range) < 0.3
            )

            if (
                cond1 and cond2 and cond3
                and cond4 and cond5
                and cond6 and cond7
            ):
                valid_15m.append(idx)

        if not valid_15m:
            return None

        # =================================
        # 5m ENTRY
        # =================================

        for i in range(2, len(df5)):

            current_time = df5.index[i]

            if current_time.time() < pd.to_datetime("09:45").time():
                continue

            if current_time.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            low_p = safe_float(row["Low"])
            close_p = safe_float(row["Close"])
            open_p = safe_float(row["Open"])
            vwap = safe_float(row["VWAP"])
            prev_high = safe_float(prev["High"])

            if None in [
                low_p, close_p,
                open_p, vwap,
                prev_high
            ]:
                continue

            latest_trigger = None

            for trigger in valid_15m:
                if trigger < current_time:
                    diff = current_time - trigger

                    if diff <= pd.Timedelta(minutes=60):
                        latest_trigger = trigger

            if latest_trigger is None:
                continue

            if current_time <= latest_trigger:
                continue

            touched_vwap = (
                low_p <= vwap * 1.002
            )

            closed_above = (
                close_p > vwap
            )

            breakout = (
                close_p > prev_high
            )

            bullish = (
                close_p > open_p
            )

            if not (
                touched_vwap
                and closed_above
                and breakout
                and bullish
            ):
                continue

            entry = round(close_p, 2)
            sl = round(vwap, 2)

            risk = entry - sl

            if risk <= 0:
                continue

            if risk < (entry * 0.003):
                continue

            target = round(
                entry + risk * 2,
                2
            )

            result = "OPEN"

            for j in range(i + 1, len(df5)):
                future = df5.iloc[j]

                f_low = safe_float(future["Low"])
                f_high = safe_float(future["High"])

                if f_low is None or f_high is None:
                    continue

                if f_low <= sl:
                    result = "LOSS"
                    break

                if f_high >= target:
                    result = "WIN"
                    break

            return {
                "stock": stock,
                "trigger": str(latest_trigger),
                "entry_time": str(current_time),
                "entry": entry,
                "sl": sl,
                "target": target,
                "result": result
            }

        return None

    except Exception as e:
        return f"ERROR: {str(e)}"


# =========================================================
# RANGE SCAN
# =========================================================

def range_scan(stock, start_date, end_date):
    results = []

    current = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    while current <= end:
        day = current.strftime("%Y-%m-%d")

        result = find_trade(stock, day)

        if result and not isinstance(result, str):
            results.append(result)

        current += timedelta(days=1)

    return results


# =========================================================
# DATE SCAN → FULL WATCHLIST
# =========================================================

def full_date_scan(date):
    results = []

    for stock in WATCHLIST:
        print("Checking:", stock)

        result = find_trade(stock, date)

        if result and not isinstance(result, str):
            results.append(result)

    return results


# =========================================================
# TELEGRAM HANDLER
# =========================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # LIVE
    if text.upper() == "LIVE":
        today = datetime.now().strftime("%Y-%m-%d")

        await update.message.reply_text(
            f"Scanning LIVE ({today})..."
        )

        results = full_date_scan(today)

        if not results:
            await update.message.reply_text(
                "❌ No live trades found"
            )
            return

        msg = f"🔥 LIVE RESULT - {today}\n\n"

        for r in results:
            msg += (
                f"{r['stock']}\n"
                f"15m: {r['trigger']}\n"
                f"5m: {r['entry_time']}\n"
                f"Entry: {r['entry']} | "
                f"SL: {r['sl']} | "
                f"Target: {r['target']}\n"
                f"Result: {r['result']}\n\n"
            )

        await update.message.reply_text(msg)
        return

    # DATE ONLY
    if len(text) == 10 and text.count("-") == 2:
        try:
            pd.to_datetime(text)

            await update.message.reply_text(
                f"Scanning full F&O for {text}"
            )

            results = full_date_scan(text)

            if not results:
                await update.message.reply_text(
                    "❌ No trades found"
                )
                return

            msg = f"🔥 DATE RESULT - {text}\n\n"

            for r in results:
                msg += (
                    f"{r['stock']}\n"
                    f"15m: {r['trigger']}\n"
                    f"5m: {r['entry_time']}\n"
                    f"Entry: {r['entry']} | "
                    f"SL: {r['sl']} | "
                    f"Target: {r['target']}\n"
                    f"Result: {r['result']}\n\n"
                )

            await update.message.reply_text(msg)
            return

        except:
            pass

    # STOCK + RANGE
    if " to " in text.lower():
        try:
            left, end_date = text.lower().split(" to ")
            parts = left.split()

            stock = parts[0].upper() + ".NS"
            start_date = parts[1]
            end_date = end_date.strip()

            await update.message.reply_text(
                f"Scanning {stock}\n"
                f"{start_date} to {end_date}"
            )

            results = range_scan(
                stock,
                start_date,
                end_date
            )

            if not results:
                await update.message.reply_text(
                    "❌ No trades found"
                )
                return

            msg = f"🔥 RANGE RESULT - {stock}\n\n"

            for r in results:
                msg += (
                    f"15m: {r['trigger']}\n"
                    f"5m: {r['entry_time']}\n"
                    f"Entry: {r['entry']} | "
                    f"SL: {r['sl']} | "
                    f"Target: {r['target']}\n"
                    f"Result: {r['result']}\n\n"
                )

            await update.message.reply_text(msg)
            return

        except:
            pass

    # STOCK + DATE
    parts = text.split()

    if len(parts) == 2:
        try:
            stock = parts[0].upper() + ".NS"
            date = parts[1]

            pd.to_datetime(date)

            await update.message.reply_text(
                f"Checking {stock} on {date}"
            )

            result = find_trade(stock, date)

            if result is None:
                await update.message.reply_text(
                    "❌ No trade found"
                )
                return

            if isinstance(result, str):
                await update.message.reply_text(result)
                return

            msg = (
                f"🔥 TRADE FOUND\n\n"
                f"Stock: {result['stock']}\n"
                f"15m: {result['trigger']}\n"
                f"5m: {result['entry_time']}\n"
                f"Entry: {result['entry']}\n"
                f"SL: {result['sl']}\n"
                f"Target: {result['target']}\n"
                f"Result: {result['result']}"
            )

            await update.message.reply_text(msg)
            return

        except:
            pass

    # HELP
    await update.message.reply_text(
        "Use these 4 formats:\n\n"
        "1. LIVE\n\n"
        "2. 2026-04-06\n\n"
        "3. BHEL 2026-04-06\n\n"
        "4. BHEL 2026-04-01 to 2026-04-20"
    )


# =========================================================
# START BOT
# =========================================================

async def main():
    print("BOT RUNNING...")

    app = ApplicationBuilder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
