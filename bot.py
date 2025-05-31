import logging
import os
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from typing import Dict, List

class GG4NEXTWINBot:
    def __init__(self, token: str, admin_group_id: str):
        self.token = token
        self.admin_group_id = admin_group_id
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.setup_database()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('gg4nextwin.log'),
                logging.StreamHandler()
            ]
        )

    def setup_database(self):
        self.conn = sqlite3.connect('gg4nextwin.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id TEXT PRIMARY KEY,
                username TEXT,
                one_x_bet_id TEXT,
                cashback_points REAL DEFAULT 0,
                rank_level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referrer_id TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id TEXT,
                amount REAL,
                payment_method TEXT,
                payment_slip_url TEXT,
                status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'processed')) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id TEXT,
                referral_id TEXT,
                earned_cashback REAL DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        for query in queries:
            self.cursor.executescript(query)
        self.conn.commit()

    async def execute_query(self, query: str, params: tuple = None):
        loop = asyncio.get_running_loop()
        if params is None:
            return await loop.run_in_executor(self.executor, self.cursor.execute, query)
        return await loop.run_in_executor(self.executor, self.cursor.execute, query, params)

    async def execute_script(self, script: str):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self.cursor.executescript, script)

    async def commit(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self.conn.commit)

    # ---------- Handlers ----------

    async def start(self, update: Update, context):
        user_id = str(update.effective_user.id)
        username = update.effective_user.username

        # Register user
        await self.execute_query(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await self.commit()

        # Send main menu
        await context.bot.send_message(
            chat_id=user_id,
            text="Welcome to GG4NEXTWIN!\n\nAvailable options:",
            reply_markup=InlineKeyboardMarkup(self.get_main_menu_keyboard())
        )

    def get_main_menu_keyboard(self) -> List[List[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton("Deposit", callback_data="deposit")],
            [InlineKeyboardButton("Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("New Account", callback_data="new_account")],
            [InlineKeyboardButton("Cashback Points", callback_data="cashback")],
            [InlineKeyboardButton("Referral Link", callback_data="referral")],
            [InlineKeyboardButton("Help", callback_data="help")],
            [InlineKeyboardButton("Check Rank", callback_data="rank")]
        ]

    async def button_callback(self, update: Update, context):
        query = update.callback_query
        user_id = str(query.from_user.id)
        data = query.data

        if data == "deposit":
            await context.bot.send_message(
                chat_id=user_id,
                text="Please enter your 1xBet ID:"
            )
            context.user_data['conversation_state'] = 'awaiting_1xbet_id'
        # Add more button logic here (withdraw, cashback, etc.)
        await query.answer()

    async def text_handler(self, update: Update, context):
        user_id = str(update.effective_user.id)
        text = update.message.text

        state = context.user_data.get('conversation_state')
        if state == 'awaiting_1xbet_id':
            context.user_data['one_x_bet_id'] = text
            await update.message.reply_text("Now, please enter deposit amount:")
            context.user_data['conversation_state'] = 'awaiting_deposit_amount'
        elif state == 'awaiting_deposit_amount':
            try:
                amount = float(text)
                context.user_data['amount'] = amount
                await update.message.reply_text("Now, please upload your payment slip as a photo.")
                context.user_data['conversation_state'] = 'awaiting_payslip'
            except ValueError:
                await update.message.reply_text("Invalid amount. Please enter a number.")
        else:
            await update.message.reply_text("Please use the menu to start.")

    async def photo_handler(self, update: Update, context):
        user_id = str(update.effective_user.id)
        state = context.user_data.get('conversation_state')

        if state == 'awaiting_payslip':
            file_id = update.message.photo[-1].file_id
            file = await context.bot.get_file(file_id)
            payslip_url = file.file_path

            # Save deposit to database
            await self.execute_query(
                "INSERT INTO deposits (user_telegram_id, amount, payment_method, payment_slip_url, status) VALUES (?, ?, ?, ?, 'pending')",
                (user_id, context.user_data.get('amount'), "Bank", payslip_url)
            )
            await self.commit()
            await update.message.reply_text("Deposit request received. Admin will review soon.")
            # Reset conversation
            context.user_data.clear()

    # ---------- Main Loop ----------

    async def main(self):
        application = Application.builder().token(self.token).build()
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
        application.add_handler(MessageHandler(filters.PHOTO, self.photo_handler))

        logging.info("GG4NEXTWIN Bot started.")
        await application.run_polling()

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_TOKEN')
    admin_group_id = os.getenv('ADMIN_GROUP_ID')
    if not token or not admin_group_id:
        raise ValueError("TELEGRAM_TOKEN and ADMIN_GROUP_ID environment variables are required")
    bot = GG4NEXTWINBot(token, admin_group_id)
    asyncio.run(bot.main())
