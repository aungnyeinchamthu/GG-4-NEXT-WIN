import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("👋 Hello! The bot is running!")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        url_path=f"{BOT_TOKEN}",
        webhook_url=f"https://gg-4-next-win-production.up.railway.app/{BOT_TOKEN}"
    )
    await app.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
