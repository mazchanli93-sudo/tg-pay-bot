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
            json={
                "asset": "USDT",
                "amount": str(PRICE_USDT),
                "description": "Публикация в чате",
                "expires_in": 3600,
                "payload": str(user_id),
            }
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

async def handle_message(update: Update, context
