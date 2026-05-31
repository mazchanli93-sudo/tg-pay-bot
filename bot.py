import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import httpx
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CRYPTO_BOT_TOKEN = os.environ.get("CRYPTO_BOT_TOKEN")
PRICE_USDT = 1.0
CRYPTO_API = "https://pay.crypt.bot/api"
pending_messages = {}

async def create_invoice(user_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CRYPTO_API}/createInvoice",
            headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN},
            json={"asset": "USDT", "amount": str(PRICE_USDT), "description": "Публикация в чате", "expires_in": 60, "payload": str(user_id)}
        )
        return resp.json()["result"]

async def check_invoice(invoice_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CRYPTO_API}/getInvoices",
            headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN},
            params={"invoice_ids": str(invoice_id)}
        )
        items = resp.json()["result"]["items"]
        return bool(items and items[0]["status"] == "paid")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user
    name = f"@{user.username}" if user.username else user.first_name
    invoice = await create_invoice(user.id)
    invoice_id = invoice["invoice_id"]
    pay_url = invoice["bot_invoice_url"]
    pending_messages[user.id] = {"text": msg.text, "chat_id": msg.chat_id, "invoice_id": invoice_id}
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить 1 USDT", url=pay_url)],
        [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_{user.id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{user.id}")]
    ]
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"💬 Ваше сообщение:\n«{msg.text}»\n\n💳 Стоимость: *1 USDT*\n\n1. Нажмите «Оплатить»\n2. После оплаты нажмите «Проверить оплату»",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await context.bot.delete_message(msg.chat_id, msg.message_id)
    except Exception:
        await context.bot.send_message(
            chat_id=msg.chat_id,
            text=f"{name}, для публикации напишите боту в личку: @Bitminskpaybot — затем повторите."
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split("_")[1])
    if data.startswith("check_"):
        pending = pending_messages.get(user_id)
        if not pending:
            await query.edit_message_text("⚠️ Сообщение не найдено.")
            return
        paid = await check_invoice(pending["invoice_id"])
        if paid:
            sender = query.from_user
            await context.bot.send_message(
                chat_id=pending["chat_id"],
                text=f"📢 *{sender.first_name}:*\n{pending['text']}",
                parse_mode="Markdown"
            )
            del pending_messages[user_id]
            await query.edit_message_text("✅ Оплата подтверждена! Сообщение опубликовано.")
        else:
            await query.edit_message_text(
                text=query.message.text + "\n\n⏳ Оплата не найдена. Попробуйте ещё раз.",
                reply_markup=query.message.reply_markup
            )
    elif data.startswith("cancel_"):
        pending_messages.pop(user_id, None)
        await query.edit_message_text("❌ Публикация отменена.")

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
