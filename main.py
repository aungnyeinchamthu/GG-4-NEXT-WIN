import os
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

# Load bot token and admin chat ID from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN environment variable is missing")
if ADMIN_CHAT_ID is None:
    raise ValueError("ADMIN_CHAT_ID environment variable is missing")

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! This is the GG 4 NEXT WIN bot ✅")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to begin or /help for help.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Webhook configuration for Railway
    port = int(os.environ.get("PORT", 8000))
    webhook_path = f"/webhook/{BOT_TOKEN}"
    webhook_url = f"https://gg-4-next-win-production.up.railway.app{webhook_path}"

    print(f"Starting webhook on {webhook_url}")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_path=webhook_path,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
