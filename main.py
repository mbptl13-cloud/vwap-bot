import os
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
# TELEGRAM TOKEN
# =========================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in Environment Variables")


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
# MAIN STRATEGY LOGIC
# =========================================

def find_trade(stock, date):
    """
    Strategy:
    1. 15m bullish candle after 9:30 with strong volume
    2. 5m pullback near VWAP
    3. Price should not close below VWAP
    4. Breakout candle confirmation
    5. Entry only between 9:45 to 1:30
    6. One trade per stock per day
    """

    try:
        start = date
        end = pd.to_datetime(date) + pd.Timedelta(days=1)

        # -----------------------------
        # Download Data
        # -----------------------------
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

        # -----------------------------
        # Convert Time to IST
        # -----------------------------
        if df15.index.tz is not None:
            df15.index = df15.index.tz_convert("Asia/Kolkata").tz_localize(None)

        if df5.index.tz is not None:
            df5.index = df5.index.tz_convert("Asia/Kolkata").tz_localize(None)

        # -----------------------------
        # VWAP
        # -----------------------------
        df5 = calculate_vwap(df5)

        # =====================================
        # STEP 1 → FIND VALID 15m TRIGGERS
        # =====================================

        valid_15m_signals = []

        avg_volume_15m = df15["Volume"].mean()

        for idx, row in df15.iterrows():

            # Ignore before 9:30
            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            bullish = row["Close"] > row["Open"]
            strong_volume = row["Volume"] > avg_volume_15m

            if bullish and strong_volume:
                valid_15m_signals.append(idx)

        if not valid_15m_signals:
            return None

        # =====================================
        # STEP 2 → FIND 5m ENTRY
        # =====================================

        used_trigger = None

        for i in range(2, len(df5)):

            current_time = df5.index[i]

            # Entry time filter
            if current_time.time() < pd.to_datetime("09:45").time():
                continue

            if current_time.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            # ---------------------------------
            # Find latest valid 15m trigger
            # within 60 mins
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
            # Breakout Confirmation
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

            # Minimum SL filter
            risk = entry - sl

            if risk <= 0:
                continue

            if risk < (entry * 0.003):  # 0.3%
                continue

            target = round(entry + (risk * 2), 2)

            # ---------------------------------
            # Result Check
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

            used_trigger = latest_trigger

            return {
                "stock": stock,
                "all_15m_signals": [str(x) for x in valid_15m_signals],
                "used_trigger": str(used_trigger),
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

    # Format:
    # BHEL 2026-04-16

    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "Use format:\n\nSTOCKNAME YYYY-MM-DD\n\nExample:\nBHEL 2026-04-16"
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
# START BOT
# =========================================

def main():
    print("BOT RUNNING...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
