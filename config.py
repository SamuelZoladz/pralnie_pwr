import os
from dotenv import load_dotenv

load_dotenv()

# Telegram bot token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# URLs for the laundry service (serwis pralni)
PRALNIE_LOGIN_URL = "https://pralnie.org/index.php/account/login"
PRALNIE_ACCOUNT_URL = "https://pralnie.org/index.php/account/index"
