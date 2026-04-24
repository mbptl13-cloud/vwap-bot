import yfinance as yf
import pandas as pd
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# =========================
# VWAP Calculation
# =========================

def calculate_vwap(df):
    df["cum_vol"] = df["Volume"].cumsum()
    df["cum_vol_price"] = (df["Close"] * df["Volume"]).cumsum()
    df["VWAP"] = df["cum_vol_price"] / df["cum_vol"]
    return df


# =========================
# Core Strategy
# =========================

def find_trade(stock, date):
    try:
        start = date
        end = pd.to_datetime(date) + pd.Timedelta(days=1)

        df15 = yf.download(
            stock,
            interval="15m",
            start=start,
            end=end,
            progress=False
        )

        df5 = yf.download(
            stock,
            interval="5m",
            start=start,
            end=end,
            progress=False
        )

        if len(df15) < 5 or len(df5) < 10:
            return None

        df15.index = df15.index.tz_localize(None) + pd.Timedelta(hours=5, minutes=30)
        df5.index = df5.index.tz_localize(None) + pd.Timedelta(hours=5, minutes=30)

        df5 = calculate_vwap(df5)

        valid_15m = []

        # Step 1 → 15m trigger
        for idx, row in df15.iterrows():

            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            if row["Close"] > row["Open"] and row["Volume"] > df15["Volume"].mean():
                valid_15m.append(idx)

        if not valid_15m:
            return None

        # Step 2 → 5m entry
        for i in range(2, len(df5)):
            now = df5.index[i]

            if now.time() < pd.to_datetime("09:45").time():
                continue

            if now.time() > pd.to_datetime("13:30").time():
                break

            row = df5.iloc[i]
            prev = df5.iloc[i - 1]

            latest_trigger = None

            for t in valid_15m:
                if t < now and (now - t) <= pd.Timedelta(minutes=60):
                    latest_trigger = t

            if latest_trigger is None:
                continue

            # Pullback near VWAP
            if not (
                row["Low"] <= row["VWAP"] * 1.002
                and row["Close"] > row["VWAP"]
            ):
                continue

            # Breakout confirmation
            if not (
                row["Close"] > prev["High"]
                and row["Close"] > row["Open"]
            ):
                continue

            entry = round(float(row["Close"]), 2)
            sl = round(float(row["VWAP"]), 2)

            if (entry - sl) < entry * 0.003:
                continue

            target = round(entry + (entry - sl) * 2, 2)

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
                "trigger": str(latest_trigger),
                "entry_time": str(now),
                "entry": entry,
                "sl": sl,
                "target": target,
                "result": result
            }

        return None

    except Exception:
        return None


# =========================
# Telegram Message Handler
# =========================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    parts = text.split()

    if len(parts) != 2:
        await update.message.reply_text(
            "Use format:\n\nBHEL 2026-04-16"
        )
        return

    stock = parts[0].upper() + ".NS"
    date = parts[1]

    result = find_trade(stock, date)

    if not result:
        await update.message.reply_text(
            f"❌ No trade found for {stock}"
        )
        return

    msg = f"""
🔥 TRADE FOUND — {stock}

15m Trigger: {result['trigger']}
5m Entry: {result['entry_time']}

Entry: {result['entry']}
SL: {result['sl']}
Target: {result['target']}

Result: {result['result']}
"""

    await update.message.reply_text(msg)


# =========================
# Start Bot
# =========================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle
    )
)

print("BOT RUNNING...")

app.run_polling()
