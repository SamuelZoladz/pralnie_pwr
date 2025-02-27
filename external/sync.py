import random
import re
import threading
import time
from datetime import datetime

import requests

from config import PRALNIE_ACCOUNT_URL


def fetch_account_balance(cookie_data: str) -> str:
    """
    Retrieves account balance using cookie data.
    Returns the account balance (with current date and time) or None if an error occurred.
    """
    headers = {"Cookie": cookie_data}
    response = requests.get(PRALNIE_ACCOUNT_URL, headers=headers)
    if response.status_code != 200:
        return None
    match = re.search(
        r"<span>\s*Stan Twojego konta\s*</span>\s*<big>\s*([^<]+?)\s*</big>",
        response.text
    )
    if match:
        return match.group(1) + ' ' + datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    return None


def start_sync_account_balance(cookie_data: str, chat_id: int, user_account_balance: dict):
    """
    Starts a daemon thread that synchronizes the account balance
    for the given chat_id every ~15 minutes (± 1 minute).
    """

    def _sync():
        base_interval = 15 * 60  # 15 minutes in seconds
        while True:
            sleep_time = base_interval + random.randint(-60, 60)
            new_balance = fetch_account_balance(cookie_data)
            if new_balance is not None:
                user_account_balance[chat_id] = new_balance
            time.sleep(sleep_time)

    threading.Thread(target=_sync, daemon=True).start()
