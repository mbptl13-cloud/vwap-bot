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
# BOT TOKEN
# =========================================

BOT_TOKEN = "8578450014:AAHQ_Eu9C-XIxRXD1760WL_1UQtVP4dbQW4"

# Optional:
# BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")


# =========================================
# SAFE FLOAT
# =========================================

def safe_float(value):
    try:
        if hasattr(value, "iloc"):
            return float(value.iloc[0])
        return float(value)
    except:
        return None


# =========================================
# GET F&O STOCKS
# =========================================

def get_fno_stocks():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }

        session = requests.Session()

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
# VWAP
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

        # =====================================
        # 15m FILTER
        # =====================================

        valid_15m_signals = []

        avg_15m_volume = safe_float(
            df15["Volume"].rolling(20).mean().iloc[-1]
        )

        for idx, row in df15.iterrows():

            if idx.time() <= pd.to_datetime("09:30").time():
                continue

            open_price = safe_float(row["Open"])
            high_price = safe_float(row["High"])
            low_price = safe_float(row["Low"])
            close_price = safe_float(row["Close"])
            volume = safe_float(row["Volume"])

            if None in [
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            ]:
                continue

            if open_price <= 0:
                continue

            candle_range = high_price - low_price
            body_size = abs(close_price - open_price)
            upper_wick = high_price - close_price

            if candle_range <= 0:
                continue

            # Condition 1
            cond_volume = volume > 500000

            # Condition 2
            cond_money_flow = (
                close_price * volume
            ) > 150000000

            # Condition 3
            range_percent = (
                (high_price - low_price)
                / open_price
            ) * 100

            cond_range = range_percent > 1

            # Condition 4
            body_percent = (
                body_size / open_price
            ) * 100

            cond_body = body_percent > 0.6

            # Condition 5
            cond_close_above_open = (
                close_price > open_price
            )

            # Condition 6
            cond_relative_volume = (
                avg_15m_volume is not None
                and volume > (avg_15m_volume * 2)
            )

            # Condition 7
            close_near_high = (
                (upper_wick / candle_range) < 0.3
            )

            if (
                cond_volume
                and cond_money_flow
                and cond_range
                and cond_body
                and cond_close_above_open
                and cond_relative_volume
                and close_near_high
            ):
                valid_15m_signals.append(idx)

        if not valid_15m_signals:
            return None

        # =====================================
        # 5m ENTRY
        # =====================================

        for i in range(2, len(df5)):

            current_time = df5.index[i]

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

            latest_trigger = None

            for trigger in valid_15m_signals:
                if trigger < current_time:
                    diff = current_time - trigger

                    if diff <= pd.Timedelta(minutes=60):
                        latest_trigger = trigger

            if latest_trigger is None:
                continue

            if current_time <= latest_trigger:
                continue

            # VWAP pullback
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

            # Breakout
            breakout = close_price > prev_high
            bullish_5m = close_price > open_price

            if not (
                breakout
                and bullish_5m
            ):
                continue

            # Entry
            entry = round(close_price, 2)
            sl = round(vwap_price, 2)

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

                future_low = safe_float(future["Low"])
                future_high = safe_float(future["High"])

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
# DATE SCAN (ALL STOCKS)
# =========================================

def full_date_scan(date):
    results = []

    for stock in WATCHLIST:
        result = find_trade(stock, date)

        if result and not isinstance(result, str):
            results.append(result)

    return results


# =========================================
# TELEGRAM HANDLER
# =========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # =====================================
    # 1. LIVE
    # =====================================

    if text.upper() == "LIVE":
        await update.message.reply_text(
            "Scanning LIVE F&O stocks..."
        )

        today = datetime.now().strftime("%Y-%m-%d")
        results = full_date_scan(today)

        if not results:
            await update.message.reply_text(
                "❌ No live trades found"
            )
            return

        msg = "🔥 LIVE RESULT\n\n"

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

    # =====================================
    # 2. STOCK + RANGE
    # Example:
    # BHEL 2026-04-01 to 2026-04-20
    # =====================================

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

    # =====================================
    # 3. STOCK + DATE
    # Example:
    # BHEL 2026-04-16
    # =====================================

    parts = text.split()

    if len(parts) == 2:
        try:
            stock = parts[0].upper() + ".NS"
            date = parts[1]

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

    # =====================================
    # 4. DATE ONLY
    # Example:
    # 2026-04-16
    # =====================================

    if len(text) == 10 and text.count("-") == 2:
        try:
            date = text

            await update.message.reply_text(
                f"Scanning full F&O for {date}"
            )

            results = full_date_scan(date)

            if not results:
                await update.message.reply_text(
                    "❌ No trades found"
                )
                return

            msg = f"🔥 DATE RESULT - {date}\n\n"

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

    # =====================================
    # HELP
    # =====================================

    await update.message.reply_text(
        "Use 4 formats:\n\n"
        "1. LIVE\n\n"
        "2. 2026-04-16\n\n"
        "3. BHEL 2026-04-16\n\n"
        "4. BHEL 2026-04-01 to 2026-04-20"
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
