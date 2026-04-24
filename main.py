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

# =========================================
# TELEGRAM BOT TOKEN
# =========================================

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

# Optional testing token
# BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")


# =========================================
# SAFE FLOAT FIX
# =========================================

def safe_float(value):
    """
    Fix for:
    The truth value of a Series is ambiguous
    """

    try:
        if hasattr(value, "iloc"):
            return float(value.iloc[0])
        return float(value)
    except:
        return None


# =========================================
# AUTO FETCH ALL NIFTY F&O STOCKS
# =========================================

def get_fno_stocks():
    """
    Auto fetch NSE F&O stocks for LIVE mode
    """

    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }

        session = requests.Session()

        # Required for NSE access
        session.get(
            "https://www.nseindia.com",
            headers=headers,
            timeout=10
        )

        response = session.get(
            url,
            headers=headers,
            timeout=10
        )

        data = response.json()

        stocks = []

        for item in data["data"]:
            stocks.append(item["symbol"] + ".NS")

        print(f"F&O Loaded: {len(stocks)}")

        return stocks

    except Exception as e:
        print("F&O Fetch Error:", e)

        # Fallback list
        return [
            "RELIANCE.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "SBIN.NS",
            "LT.NS",
            "PFC.NS",
            "BHEL.NS",
            "HAL.NS",
            "TRENT.NS",
            "ADANIENT.NS"
        ]


WATCHLIST = get_fno_stocks()


# =========================================
# VWAP CALCULATION
# =========================================

def calculate_vwap(df):
    df = df.copy()

    df["cum_vol"] = df["Volume"].cumsum()
    df["cum_vol_price"] = (df["Close"] * df["Volume"]).cumsum()
    df["VWAP"] = df["cum_vol_price"] / df["cum_vol"]

    return df


# =========================================
# MAIN STRATEGY
# =========================================

def find_trade(stock, date):
    """
    FINAL STRATEGY

    STEP 1:
    Strong 15m bullish trigger after 9:30

    STEP 2:
    5m VWAP pullback + close above VWAP

    STEP 3:
    Breakout above previous candle

    STEP 4:
    Entry only between 9:45 and 1:30

    STEP 5:
    One trade per stock per day
    """

    try:
        start = date
        end = pd.to_datetime(date) + pd.Timedelta(days=1)

        # ---------------------------------
        # Download 15m Data
        # ---------------------------------

        df15 = yf.download(
            stock,
            interval="15m",
            start=start,
            end=end,
            progress=False,
            auto_adjust=True
        )

        # ---------------------------------
        # Download 5m Data
        # ---------------------------------

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

        # ---------------------------------
        # Convert to IST
        # ---------------------------------

        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert(
                "Asia/Kolkata"
            ).tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert(
                "Asia/Kolkata"
            ).tz_localize(None)

        # ---------------------------------
        # VWAP
        # ---------------------------------

        df5 = calculate_vwap(df5)

        # =====================================
        # STEP 1 → STRONG VALID 15m SIGNALS
        # =====================================

        valid_15m_signals = []
        avg_15m_volume = safe_float(df15["Volume"].mean())

        for idx, row in df15.iterrows():

            # Ignore before 9:30
            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            open_price = safe_float(row["Open"])
            close_price = safe_float(row["Close"])
            high_price = safe_float(row["High"])
            low_price = safe_float(row["Low"])
            volume = safe_float(row["Volume"])

            if None in [
                open_price,
                close_price,
                high_price,
                low_price,
                volume
            ]:
                continue

            # ---------------------------------
            # Candle Structure Quality Check
            # ---------------------------------

            candle_range = high_price - low_price
            body_size = close_price - open_price
            upper_wick = high_price - close_price

            if candle_range <= 0:
                continue

            # Rule 1 → Bullish Candle
            bullish = close_price > open_price

            # Rule 2 → Strong Body
            strong_body = body_size >= (
                candle_range * 0.5
            )

            # Rule 3 → Close Near High
            close_near_high = upper_wick <= (
                candle_range * 0.3
            )

            # Rule 4 → Strong Volume
            strong_volume = volume > avg_15m_volume

            # Final strict confirmation

            if (
                bullish
                and strong_body
                and close_near_high
                and strong_volume
            ):
                valid_15m_signals.append(idx)

        if not valid_15m_signals:
            return None

        # =====================================
        # STEP 2 → 5m ENTRY LOGIC
        # =====================================

        for i in range(2, len(df5)):

            current_time = df5.index[i]

            # Entry window

            if current_time.time() < pd.to_datetime("09:45").time():
                continue

            if current_time.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            low_price = safe_float(row["Low"])
            close_price = safe_float(row["Close"])
            open_price = safe_float(row["Open"])
            vwap_price = safe_float(row["VWAP"])
            prev_high = safe_float(prev["High"])

            if None in [
                low_price,
                close_price,
                open_price,
                vwap_price,
                prev_high
            ]:
                continue

            # ---------------------------------
            # Find latest 15m trigger
            # within 60 minutes
            # ---------------------------------

            latest_trigger = None

            for trigger in valid_15m_signals:
                if trigger < current_time:
                    diff = current_time - trigger

                    if diff <= pd.Timedelta(minutes=60):
                        latest_trigger = trigger

            if latest_trigger is None:
                continue

            # No same candle entry

            if current_time <= latest_trigger:
                continue

            # ---------------------------------
            # VWAP Pullback
            # ---------------------------------

            touched_vwap = (
                low_price <= vwap_price * 1.002
            )

            closed_above_vwap = (
                close_price > vwap_price
            )

            if not (
                touched_vwap
                and closed_above_vwap
            ):
                continue

            # ---------------------------------
            # Breakout Confirmation
            # ---------------------------------

            breakout = close_price > prev_high
            bullish_5m = close_price > open_price

            if not (
                breakout
                and bullish_5m
            ):
                continue

            # ---------------------------------
            # Entry / SL / Target
            # ---------------------------------

            entry = round(close_price, 2)
            sl = round(vwap_price, 2)

            risk = entry - sl

            if risk <= 0:
                continue

            # Minimum SL Filter

            if risk < (entry * 0.003):
                continue

            target = round(
                entry + (risk * 2),
                2
            )

            # ---------------------------------
            # Result Check
            # ---------------------------------

            result = "OPEN"

            for j in range(i + 1, len(df5)):
                future = df5.iloc[j]

                future_low = safe_float(
                    future["Low"]
                )

                future_high = safe_float(
                    future["High"]
                )

                if (
                    future_low is None
                    or future_high is None
                ):
                    continue

                if future_low <= sl:
                    result = "LOSS"
                    break

                if future_high >= target:
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


# =========================================
# RANGE SCAN
# =========================================

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


# =========================================
# LIVE SCAN
# =========================================

def live_scan():
    today = datetime.now().strftime("%Y-%m-%d")
    results = []

    for stock in WATCHLIST:
        result = find_trade(stock, today)

        if result and not isinstance(result, str):
            results.append(result)

    return results


# =========================================
# TELEGRAM HANDLER
# =========================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    text = update.message.text.strip()

    # =====================================
    # LIVE MODE
    # =====================================

    if text.upper() == "LIVE":
        await update.message.reply_text(
            "Scanning LIVE NIFTY F&O opportunities..."
        )

        results = live_scan()

        if not results:
            await update.message.reply_text(
                "❌ No live trades found"
            )
            return

        msg = "🔥 LIVE F&O SIGNALS\n\n"

        for r in results:
            msg += (
                f"{r['stock']}\n"
                f"15m Trigger: {r['trigger']}\n"
                f"5m Entry: {r['entry_time']}\n"
                f"Entry: {r['entry']} | "
                f"SL: {r['sl']} | "
                f"Target: {r['target']}\n"
                f"Result: {r['result']}\n\n"
            )

        await update.message.reply_text(msg)
        return

    # =====================================
    # RANGE MODE
    # Example:
    # ADANIGREEN 2026-04-01 to 2026-04-20
    # =====================================

    if " to " in text.lower():

        try:
            left, end_date = text.lower().split(" to ")
            parts = left.split()

            stock = parts[0].upper() + ".NS"
            start_date = parts[1]
            end_date = end_date.strip()

            await update.message.reply_text(
                f"Scanning range for {stock}\n"
                f"{start_date} to {end_date}"
            )

            results = range_scan(
                stock,
                start_date,
                end_date
            )

            if not results:
                await update.message.reply_text(
                    "❌ No trades found in range"
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
            await update.message.reply_text(
                "Use format:\n"
                "ADANIGREEN 2026-04-01 to 2026-04-20"
            )
            return

    # =====================================
    # SINGLE DATE MODE
    # Example:
    # BHEL 2026-04-16
    # =====================================

    parts = text.split()

    if len(parts) == 2:
        stock = parts[0].upper() + ".NS"
        date = parts[1]

        await update.message.reply_text(
            f"Checking {stock} on {date}..."
        )

        result = find_trade(stock, date)

        if result is None:
            await update.message.reply_text(
                f"❌ No trade found for {stock}"
            )
            return

        if isinstance(result, str):
            await update.message.reply_text(result)
            return

        msg = (
            f"🔥 TRADE FOUND - {result['stock']}\n\n"
            f"15m Trigger: {result['trigger']}\n"
            f"5m Entry: {result['entry_time']}\n\n"
            f"Entry: {result['entry']}\n"
            f"SL: {result['sl']}\n"
            f"Target: {result['target']}\n"
            f"Result: {result['result']}"
        )

        await update.message.reply_text(msg)
        return

    # =====================================
    # HELP MENU
    # =====================================

    await update.message.reply_text(
        "Commands:\n\n"
        "1. Single Day:\n"
        "BHEL 2026-04-16\n\n"
        "2. Date Range:\n"
        "ADANIGREEN 2026-04-01 to 2026-04-20\n\n"
        "3. Live Full F&O Scan:\n"
        "LIVE"
    )


# =========================================
# START BOT
# =========================================

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
