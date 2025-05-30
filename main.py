import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import logging

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to GG 4 NEXT WIN Bot! Type /help to see available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 Available commands:\n/start - Welcome message\n/help - This help menu")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_url=f"https://gg-4-next-win-production.up.railway.app/webhook/{BOT_TOKEN}"
    )

# Detect if already inside an event loop
try:
    asyncio.get_running_loop().create_task(main())
except RuntimeError:
    asyncio.run(main())
