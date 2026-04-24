import os
import asyncio
import pandas as pd
import yfinance as yf

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

BOT_TOKEN = os.getenv("8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in Render Environment Variables")


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
# FIND TRADE LOGIC
# =========================================

def find_trade(stock, date):
    """
    Strategy:
    1. 15m bullish candle after 9:30
    2. Strong volume candle
    3. 5m pullback near VWAP
    4. Candle closes above VWAP
    5. Breakout confirmation
    6. Entry only between 9:45 and 1:30
    7. One trade per stock per day
    """

    try:
        start = date
        end = pd.to_datetime(date) + pd.Timedelta(days=1)

        # ---------------------------------
        # Download 15m data
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
        # Download 5m data
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
        # Convert timezone to IST
        # ---------------------------------

        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert("Asia/Kolkata").tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert("Asia/Kolkata").tz_localize(None)

        # ---------------------------------
        # Calculate VWAP
        # ---------------------------------

        df5 = calculate_vwap(df5)

        # =====================================
        # STEP 1 → VALID 15m SIGNALS
        # =====================================

        valid_15m_signals = []
        avg_15m_volume = df15["Volume"].mean()

        for idx, row in df15.iterrows():

            # Ignore before 9:30
            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            bullish = row["Close"] > row["Open"]
            strong_volume = row["Volume"] > avg_15m_volume

            if bullish and strong_volume:
                valid_15m_signals.append(idx)

        if not valid_15m_signals:
            return None

        # =====================================
        # STEP 2 → 5m ENTRY LOGIC
        # =====================================

        for i in range(2, len(df5)):

            current_time = df5.index[i]

            # Entry allowed only 9:45 to 1:30

            if current_time.time() < pd.to_datetime("09:45").time():
                continue

            if current_time.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            # ---------------------------------
            # Find latest valid trigger
            # within last 60 mins
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

            touched_vwap = row["Low"] <= row["VWAP"] * 1.002
            closed_above_vwap = row["Close"] > row["VWAP"]

            if not (touched_vwap and closed_above_vwap):
                continue

            # ---------------------------------
            # Breakout confirmation
            # ---------------------------------

            breakout = row["Close"] > prev["High"]
            bullish_5m = row["Close"] > row["Open"]

            if not (breakout and bullish_5m):
                continue

            # ---------------------------------
            # Entry / SL / Target
            # ---------------------------------

            entry = round(float(row["Close"]), 2)
            sl = round(float(row["VWAP"]), 2)

            risk = entry - sl

            # Minimum SL filter

            if risk <= 0:
                continue

            if risk < (entry * 0.003):  # 0.3%
                continue

            target = round(entry + (risk * 2), 2)

            # ---------------------------------
            # Result check
            # ---------------------------------

            result = "OPEN"

            for j in range(i + 1, len(df5)):
                future = df5.iloc[j]

                if future["Low"] <= sl:
                    result = "LOSS"
                    break

                if future["High"] >= target:
                    result = "WIN"
                    break

            return {
                "stock": stock,
                "all_15m_signals": [str(x) for x in valid_15m_signals],
                "used_trigger": str(latest_trigger),
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
# TELEGRAM MESSAGE HANDLER
# =========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Example:
    # BHEL 2026-04-16

    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "Use format:\n\n"
            "STOCKNAME YYYY-MM-DD\n\n"
            "Example:\n"
            "BHEL 2026-04-16"
        )
        return

    stock = parts[0].upper() + ".NS"
    date = parts[1]

    await update.message.reply_text(
        f"Checking trade for {stock} on {date}..."
    )

    result = find_trade(stock, date)

    if result is None:
        await update.message.reply_text(
            f"❌ No trade found for {stock} on {date}"
        )
        return

    if isinstance(result, str) and result.startswith("ERROR"):
        await update.message.reply_text(result)
        return

    message = f"""
🔥 TRADE FOUND — {result['stock']}

15m Signals:
{", ".join(result['all_15m_signals'])}

Used Trigger:
{result['used_trigger']}

5m Entry Time:
{result['entry_time']}

Entry Price:
{result['entry']}

Stop Loss:
{result['sl']}

Target:
{result['target']}

Result:
{result['result']}
"""

    await update.message.reply_text(message)


# =========================================
# START BOT (PYTHON 3.14 FIX)
# =========================================

async def main():
    print("BOT RUNNING...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Keep running forever
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
