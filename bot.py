import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram import Update
from telegram.ext.filters import Filters
import sqlite3
from datetime import datetime
import os
from typing import Dict, List, Optional

class GG4NEXTWINBot:
    def __init__(self, token: str, admin_group_id: str):
        self.token = token
        self.admin_group_id = admin_group_id
        self.logger = logging.getLogger(__name__)
        self.setup_database()
        self.setup_logging()
        
    def setup_database(self):
        """Initialize database connection and create necessary tables"""
        self.conn = sqlite3.connect('gg4nextwin.db')
        self.cursor = self.conn.cursor()
        self.create_tables()
        
    def create_tables(self):
        """Create required database tables"""
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
                referrer_id TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users (telegram_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id TEXT,
                amount REAL,
                payment_method TEXT,
                payment_slip_url TEXT,
                status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'processed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_telegram_id) REFERENCES users (telegram_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_telegram_id TEXT,
                amount REAL,
                withdrawal_details TEXT,
                status TEXT CHECK(status IN ('pending', 'approved', 'rejected', 'processed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_telegram_id) REFERENCES users (telegram_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id TEXT,
                referral_id TEXT,
                earned_cashback REAL DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (telegram_id),
                FOREIGN KEY (referral_id) REFERENCES users (telegram_id)
            )
            """
        ]
        
        for query in queries:
            try:
                self.cursor.executescript(query)
                self.conn.commit()
            except sqlite3.Error as e:
                self.logger.error(f"Database error creating tables: {e}")
                raise

    def setup_logging(self):
        """Configure logging for the bot"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('gg4nextwin.log'),
                logging.StreamHandler()
            ]
        )

    def start(self, update, context):
        """Handle /start command with referral system"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Check for referral link
        if context.args and len(context.args) > 0:
            referrer_id = context.args[0]
            self.logger.info(f"Referral detected: {referrer_id} referred {user_id}")
            self.process_referral(user_id, referrer_id)
        
        try:
            # Register user if new
            self.register_user(user_id, username)
            
            # Send welcome message with menu
            context.bot.send_message(
                chat_id=user_id,
                text="Welcome to GG4NEXTWIN!\n\nAvailable options:",
                parse_mode='Markdown',
                reply_markup=self.get_main_menu_keyboard()
            )
        except Exception as e:
            self.logger.error(f"Error handling start command: {e}")
            context.bot.send_message(
                chat_id=user_id,
                text="An error occurred. Please try again later."
            )

    def register_user(self, user_id: str, username: str):
        """Register or update user information"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO users (telegram_id, username)
                VALUES (?, ?)
            """, (str(user_id), username))
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error registering user: {e}")
            raise

    def process_referral(self, referral_id: str, referrer_id: str):
        """Process new referral"""
        try:
            # Check if referrer exists
            self.cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (referrer_id,))
            if self.cursor.fetchone():
                # Update referral information
                self.cursor.execute("""
                    UPDATE users 
                    SET referrer_id = ? 
                    WHERE telegram_id = ?
                """, (referrer_id, referral_id))
                self.conn.commit()
                
                # Create referral record
                self.cursor.execute("""
                    INSERT INTO referrals (referrer_id, referral_id)
                    VALUES (?, ?)
                """, (referrer_id, referral_id))
                self.conn.commit()
                
                # Calculate and award referral bonus
                self.award_referral_bonus(referrer_id)
            else:
                self.logger.warning(f"Invalid referrer ID: {referrer_id}")
        except sqlite3.Error as e:
            self.logger.error(f"Error processing referral: {e}")
            raise

    def award_referral_bonus(self, referrer_id: str):
        """Award cashback bonus to referrer"""
        try:
            # Award 0.25% of deposit amount as cashback
            bonus_percentage = 0.0025  # 0.25%
            
            self.cursor.execute("""
                UPDATE users 
                SET cashback_points = cashback_points + ? 
                WHERE telegram_id = ?
            """, (bonus_percentage, referrer_id))
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error awarding referral bonus: {e}")
            raise

    def get_main_menu_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Return main menu keyboard layout"""
        return [
            [InlineKeyboardButton("Deposit", callback_data="deposit")],
            [InlineKeyboardButton("Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("New Account", callback_data="new_account")],
            [InlineKeyboardButton("Cashback Points", callback_data="cashback")],
            [InlineKeyboardButton("Referral Link", callback_data="referral")],
            [InlineKeyboardButton("Help", callback_data="help")],
            [InlineKeyboardButton("Check Rank", callback_data="rank")]
        ]

    def get_bank_options_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Return bank options keyboard"""
        return [
            [InlineKeyboardButton("Bank A", callback_data="bank_a")],
            [InlineKeyboardButton("Bank B", callback_data="bank_b")],
            [InlineKeyboardButton("Bank C", callback_data="bank_c")]
        ]

    def button_callback(self, update, context):
        """Handle button callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            if query.data == "deposit":
                self.start_deposit_flow(user_id, context)
            elif query.data == "withdraw":
                self.start_withdraw_flow(user_id, context)
            elif query.data == "new_account":
                self.handle_new_account(user_id, context)
            elif query.data == "cashback":
                self.show_cashback(user_id, context)
            elif query.data == "referral":
                self.generate_referral_link(user_id, context)
            elif query.data == "help":
                self.show_help(user_id, context)
            elif query.data == "rank":
                self.show_rank(user_id, context)
            elif query.data.startswith("bank_"):
                self.process_bank_selection(user_id, query.data, context)
            
            query.answer()
        except Exception as e:
            self.logger.error(f"Error handling button callback: {e}")
            query.answer(text="An error occurred. Please try again.")

    def start_deposit_flow(self, user_id: int, context):
        """Start deposit flow"""
        try:
            context.bot.send_message(
                chat_id=user_id,
                text="Please enter your 1xBet ID:",
                reply_markup=self.get_cancel_keyboard()
            )
            context.user_data['conversation_state'] = 'deposit_1xbet_id'
        except Exception as e:
            self.logger.error(f"Error starting deposit flow: {e}")

    def process_1xbet_id(self, update, context):
        """Process 1xBet ID input"""
        user_id = update.effective_user.id
        one_x_bet_id = update.message.text
        
        try:
            # Validate 1xBet ID format (9-13 digits)
            if not (one_x_bet_id.isdigit() and 9 <= len(one_x_bet_id) <= 13):
                context.bot.send_message(
                    chat_id=user_id,
                    text="Invalid 1xBet ID format. Please enter 9-13 digits.",
                    reply_markup=self.get_cancel_keyboard()
                )
                return
            
            context.user_data['one_x_bet_id'] = one_x_bet_id
            context.user_data['conversation_state'] = 'deposit_amount'
            
            context.bot.send_message(
                chat_id=user_id,
                text="Enter deposit amount:",
                reply_markup=self.get_cancel_keyboard()
            )
        except Exception as e:
            self.logger.error(f"Error processing 1xBet ID: {e}")
            context.bot.send_message(
                chat_id=user_id,
                text="Error processing 1xBet ID. Please try again."
            )

    def process_deposit_amount(self, update, context):
        """Process deposit amount"""
        user_id = update.effective_user.id
        try:
            amount = float(update.message.text)
            if amount <= 0:
                context.bot.send_message(
                    chat_id=user_id,
                    text="Amount must be positive.",
                    reply_markup=self.get_cancel_keyboard()
                )
                return
            
            context.user_data['amount'] = amount
            context.user_data['conversation_state'] = 'deposit_bank'
            
            context.bot.send_message(
                chat_id=user_id,
                text="Select your bank:",
                reply_markup=InlineKeyboardMarkup(self.get_bank_options_keyboard())
            )
        except ValueError:
            context.bot.send_message(
                chat_id=user_id,
                text="Invalid amount. Please enter a valid number.",
                reply_markup=self.get_cancel_keyboard()
            )

    def process_bank_selection(self, user_id: int, bank_data: str, context):
        """Process bank selection"""
        try:
            bank = bank_data.replace("bank_", "")
            
            context.user_data['bank'] = bank
            context.user_data['conversation_state'] = 'deposit_payslip'
            
            context.bot.send_message(
                chat_id=user_id,
                text="Please upload your payment slip:",
                reply_markup=self.get_cancel_keyboard()
            )
        except Exception as e:
            self.logger.error(f"Error processing bank selection: {e}")
            context.bot.send_message(
                chat_id=user_id,
                text="Error processing bank selection. Please try again."
            )

    def process_payslip(self, update, context):
        """Process payment slip"""
        user_id = update.effective_user.id
        file_id = update.message.photo[-1].file_id
        
        try:
            # Download and validate payment slip
            file_path = context.bot.get_file(file_id).file_path
            
            # Store deposit information
            deposit_data = {
                'user_id': user_id,
                'amount': context.user_data['amount'],
                'bank': context.user_data['bank'],
                'payslip_url': file_path,
                'one_x_bet_id': context.user_data['one_x_bet_id']
            }
            
            self.store_deposit(deposit_data)
            self.notify_admin_group("New deposit request received")
            
            # Reset conversation state
            context.user_data.clear()
            
            context.bot.send_message(
                chat_id=user_id,
                text="Deposit request received successfully. Admin will review it shortly."
            )
        except Exception as e:
            self.logger.error(f"Error processing payslip: {e}")
            context.bot.send_message(
                chat_id=user_id,
                text="Error processing payment slip. Please try again."
            )

    def store_deposit(self, deposit_data: Dict):
        """Store deposit information in database"""
        try:
            self.cursor.execute("""
                INSERT INTO deposits (user_telegram_id, amount, payment_method, payment_slip_url, one_x_bet_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(deposit_data['user_id']),
                deposit_data['amount'],
                deposit_data['bank'],
                deposit_data['payslip_url'],
                deposit_data['one_x_bet_id']
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error storing deposit: {e}")
            raise

    def notify_admin_group(self, message: str):
        """Notify admin group about new deposit"""
        try:
            keyboard = [
                [InlineKeyboardButton("Approve", callback_data="approve"),
                 InlineKeyboardButton("Reject", callback_data="reject")]
            ]
            
            self.updater.bot.send_message(
                chat_id=self.admin_group_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            self.logger.error(f"Error notifying admin group: {e}")

    def get_cancel_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Return cancel keyboard"""
        return [[InlineKeyboardButton("Cancel", callback_data="cancel")]]

    def run(self):
        """Start the bot"""
        self.updater = Updater(self.token)
        dp = self.updater.dispatcher
        
        # Register handlers
        dp.add_handler(CommandHandler("start", self.start))
        dp.add_handler(CallbackQueryHandler(self.button_callback))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        # Start the bot
        self.updater.start_polling()
        self.logger.info("GG4NEXTWIN Bot started. Press Ctrl-C to exit.")
        self.updater.idle()

if __name__ == '__main__':
    # Load environment variables
    token = os.getenv('TELEGRAM_TOKEN')
    admin_group_id = os.getenv('ADMIN_GROUP_ID')
    
    if not token or not admin_group_id:
        raise ValueError("TELEGRAM_TOKEN and ADMIN_GROUP_ID environment variables are required")
    
    # Create and run bot
    bot = GG4NEXTWINBot(token, admin_group_id)
    bot.run()
