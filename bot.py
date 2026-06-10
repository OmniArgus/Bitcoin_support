"""Telegram bot that reports the Bitcoin price and notifies on large moves.

Features
--------
* /start  - subscribe the current chat to price-move notifications
* /stop   - unsubscribe
* /price  - get the current BTC price on demand
* /threshold [usd] - view or change how big a move triggers a notification

A background job polls CoinGecko and, whenever the price has moved by at least
the configured threshold (default $500) since the last notification, it pushes
an update to every subscribed chat.
"""

import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from storage import Storage

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
COIN_ID = os.getenv("COIN_ID", "bitcoin").strip()
VS_CURRENCY = os.getenv("VS_CURRENCY", "usd").strip()
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
DEFAULT_THRESHOLD = float(os.getenv("THRESHOLD", "30"))
ADMIN_IDS = {
    int(uid)
    for uid in os.getenv("ADMIN_IDS", "").replace(",", " ").split()
    if uid.strip()
}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

storage = Storage(os.getenv("STATE_FILE", "state.json"))


async def fetch_price() -> float:
    """Return the current price of COIN_ID in VS_CURRENCY from CoinGecko."""
    params = {"ids": COIN_ID, "vs_currencies": VS_CURRENCY}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(COINGECKO_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    return float(data[COIN_ID][VS_CURRENCY])


def format_price(price: float) -> str:
    symbol = "$" if VS_CURRENCY == "usd" else ""
    return f"{symbol}{price:,.2f} {VS_CURRENCY.upper()}"


def is_admin(user_id: int | None) -> bool:
    """Only configured admins may change settings. If ADMIN_IDS is empty,
    nobody is treated as admin (the threshold becomes read-only)."""
    return user_id is not None and user_id in ADMIN_IDS


# --- Command handlers -------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    storage.subscribe(chat_id)
    threshold = storage.get_threshold(DEFAULT_THRESHOLD)
    await update.message.reply_text(
        "✅ You're subscribed!\n\n"
        f"I'll notify you whenever {COIN_ID.title()} moves by "
        f"{format_price(threshold)} or more.\n\n"
        "Commands:\n"
        "/price - current price\n"
        "/threshold <usd> - set the move size that triggers an alert\n"
        "/stop - unsubscribe"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    storage.unsubscribe(chat_id)
    await update.message.reply_text("🛑 Unsubscribed. Send /start to re-enable alerts.")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        current = await fetch_price()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Price fetch failed: %s", exc)
        await update.message.reply_text("⚠️ Couldn't fetch the price right now. Try again shortly.")
        return
    await update.message.reply_text(
        f"💰 {COIN_ID.title()}: *{format_price(current)}*",
        parse_mode=ParseMode.MARKDOWN,
    )


async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        user = update.effective_user
        if not is_admin(user.id if user else None):
            await update.message.reply_text(
                "⛔ Only an admin can change the alert threshold."
            )
            return
        try:
            value = float(context.args[0].replace(",", "").replace("$", ""))
            if value <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Usage: /threshold 500")
            return
        storage.set_threshold(value)
        await update.message.reply_text(
            f"✅ Alert threshold set to {format_price(value)}."
        )
    else:
        current = storage.get_threshold(DEFAULT_THRESHOLD)
        await update.message.reply_text(
            f"Current alert threshold: {format_price(current)}.\n"
            "Change it with /threshold <usd>, e.g. /threshold 1000"
        )


# --- Background polling job --------------------------------------------------


async def check_price(context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribers = storage.subscribers()
    if not subscribers:
        return

    try:
        current = await fetch_price()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Polling fetch failed: %s", exc)
        return

    last = storage.get_last_price()
    if last is None:
        storage.set_last_price(current)
        return

    move = current - last
    threshold_value = storage.get_threshold(DEFAULT_THRESHOLD)
    if abs(move) < threshold_value:
        return

    direction = "📈 up" if move > 0 else "📉 down"
    text = (
        f"{direction} {format_price(abs(move))}!\n\n"
        f"{COIN_ID.title()} is now *{format_price(current)}*\n"
        f"(was {format_price(last)})"
    )
    storage.set_last_price(current)

    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to notify %s: %s", chat_id, exc)


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN is not set. Create a bot with @BotFather and put the "
            "token in a .env file (see .env.example)."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("threshold", threshold))

    app.job_queue.run_repeating(check_price, interval=POLL_SECONDS, first=5)

    logger.info("Bot started. Polling every %ss.", POLL_SECONDS)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
