import logging
import os
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv
from bot import handlers

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Build the Telegram bot application
app = Application.builder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', handlers.start)],
    states={
        handlers.EXTERNAL_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.external_login)],
        handlers.EXTERNAL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.external_password)]
    },
    fallbacks=[CommandHandler('cancel', handlers.cancel)]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler('stan', handlers.stan))
app.add_handler(CommandHandler('doladuj', handlers.doladuj))

# Run the bot
app.run_polling()
