# FULL FINAL HYBRID VWAP TELEGRAM BOT
# WITH:
# 1. Full F&O Hybrid Watchlist
# 2. 15m Institutional Filter (Pass/Fail)
# 3. 5m VWAP Price Action Score (Out of 5)
# 4. Only Score >= 4 Allowed
# 5. Commands:
#    LIVE
#    2026-04-06
#    BHEL 2026-04-06
#    BHEL 2026-04-01 to 2026-04-20

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

# =====================================================
# BOT TOKEN
# =====================================================

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

# Optional direct token
# BOT_TOKEN = "YOUR_BOT_TOKEN"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")


# =====================================================
# SAFE FLOAT
# =====================================================

def safe_float(value):
    try:
        if hasattr(value, "iloc"):
            return float(value.iloc[0])
        return float(value)
    except:
        return None


# =====================================================
# HYBRID FULL F&O WATCHLIST
# =====================================================

def get_fno_stocks():
    backup_stocks = [
        "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS",
        "BAJFINANCE.NS", "BAJAJFINSV.NS",
        "PFC.NS", "RECLTD.NS",
        "TCS.NS", "INFY.NS", "WIPRO.NS",
        "HCLTECH.NS", "TECHM.NS",
        "LT.NS", "BHEL.NS", "HAL.NS", "BEL.NS",
        "SIEMENS.NS", "ABB.NS",
        "ADANIENT.NS", "ADANIPORTS.NS",
        "ADANIGREEN.NS", "ADANIPOWER.NS", "ATGL.NS",
        "TATASTEEL.NS", "JSWSTEEL.NS",
        "HINDALCO.NS", "VEDL.NS",
        "TATAMOTORS.NS", "MARUTI.NS", "M&M.NS",
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS",
        "ITC.NS", "HINDUNILVR.NS",
        "TRENT.NS", "KAYNES.NS", "POLICYBZR.NS",
        "AMBER.NS", "INOXWIND.NS"
    ]

    try:
        session = requests.Session()

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
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

        final_watchlist = list(
            set(live_stocks + backup_stocks)
        )

    except:
        final_watchlist = backup_stocks

    must_have = [
        "ADANIGREEN.NS",
        "ADANIPOWER.NS",
        "TRENT.NS",
        "BHEL.NS",
        "PFC.NS",
        "HAL.NS"
    ]

    for stock in must_have:
        if stock not in final_watchlist:
            final_watchlist.append(stock)

    final_watchlist = list(set(final_watchlist))
    final_watchlist.sort()

    print("WATCHLIST SIZE:", len(final_watchlist))

    return final_watchlist


WATCHLIST = get_fno_stocks()


# =====================================================
# VWAP CALCULATION
# =====================================================

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


# =====================================================
# MAIN STRATEGY
# =====================================================

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

        # =========================================
        # STEP 1 → 15m FILTER (PASS / FAIL)
        # =========================================

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

            if None in [
                open_p, high_p,
                low_p, close_p, vol
            ]:
                continue

            candle_range = high_p - low_p
            body = abs(close_p - open_p)
            upper_wick = high_p - close_p

            if candle_range <= 0:
                continue

            cond1 = vol > 500000
            cond2 = (close_p * vol) > 150000000

            range_percent = (
                (high_p - low_p) / open_p
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

        # =========================================
        # STEP 2 → 5m VWAP SCORE (OUT OF 5)
        # =========================================

        for i in range(2, len(df5)):

            current_time = df5.index[i]

            if current_time.time() < pd.to_datetime("09:45").time():
                continue

            if current_time.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            low_p = safe_float(row["Low"])
            high_p = safe_float(row["High"])
            close_p = safe_float(row["Close"])
            open_p = safe_float(row["Open"])
            vol = safe_float(row["Volume"])
            vwap = safe_float(row["VWAP"])
            prev_high = safe_float(prev["High"])

            if None in [
                low_p, high_p,
                close_p, open_p,
                vol, vwap,
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

            # =========================================
            # VWAP SCORE SYSTEM
            # =========================================

            score = 0

            # 1. Clean VWAP Touch
            if low_p <= vwap * 1.002:
                score += 1

            # 2. Strong Rejection
            wick_rejection = (
                (close_p - low_p)
                > ((high_p - low_p) * 0.5)
            )

            if wick_rejection:
                score += 1

            # 3. Bullish Close Above VWAP
            if close_p > vwap:
                score += 1

            # 4. Breakout Above Previous High
            if close_p > prev_high:
                score += 1

            # 5. Volume Expansion
            avg_5m_vol = safe_float(
                df5["Volume"].rolling(20).mean().iloc[i]
            )

            if (
                avg_5m_vol is not None
                and vol > avg_5m_vol * 1.5
            ):
                score += 1

            # Only strong setups allowed
            if score < 4:
                continue

            # =========================================
            # ENTRY
            # =========================================

            entry = round(close_p, 2)
            sl = round(vwap, 2)

            risk = entry - sl

            if risk <= 0:
                continue

            if risk < (entry * 0.003):
                continue

            target = round(
                entry + (risk * 2),
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
                "score": f"{score}/5",
                "entry": entry,
                "sl": sl,
                "target": target,
                "result": result
            }

        return None

    except Exception as e:
        return f"ERROR: {str(e)}"


# =====================================================
# DATE SCAN → FULL WATCHLIST
# =====================================================

def full_date_scan(date):
    results = []

    for stock in WATCHLIST:
        result = find_trade(stock, date)

        if result and not isinstance(result, str):
            results.append(result)

    return results


# =====================================================
# RANGE SCAN
# =====================================================

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


# =====================================================
# TELEGRAM HANDLER
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if len(text) == 10 and text.count("-") == 2:
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
                f"VWAP Score: {r['score']}\n"
                f"Entry: {r['entry']} | "
                f"SL: {r['sl']} | "
                f"Target: {r['target']}\n"
                f"Result: {r['result']}\n\n"
            )

        await update.message.reply_text(msg)
        return

    await update.message.reply_text(
        "Use:\n"
        "LIVE\n"
        "2026-04-06\n"
        "BHEL 2026-04-06\n"
        "BHEL 2026-04-01 to 2026-04-20"
    )


# =====================================================
# START BOT
# =====================================================

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
