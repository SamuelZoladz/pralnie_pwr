import logging
import random
import re
import threading
import time
from datetime import datetime

import requests

from bot.db import UserDatabase
from config import PRALNIE_ACCOUNT_URL


def fetch_account_balance(cookie_data: str) -> str:
    """
    Retrieves account balance using cookie data.
    Returns the account balance (with current date and time) or None if an error occurred.
    """
    logging.debug("Fetching account balance...")
    headers = {"Cookie": cookie_data}
    response = requests.get(PRALNIE_ACCOUNT_URL, headers=headers)

    if response.status_code != 200:
        logging.warning(f"Failed to fetch account balance: HTTP {response.status_code}")
        return None

    match = re.search(
        r"<span>\s*Stan Twojego konta\s*</span>\s*<big>\s*([^<]+?)\s*</big>",
        response.text
    )

    if match:
        balance = match.group(1)
        logging.debug(f"Account balance fetched successfully: {balance}")
        return balance

    logging.warning("Account balance not found in response.")
    return None


def start_sync_account_balance(chat_id: int):
    """
    Starts a daemon thread that synchronizes the account balance
    for the given chat_id every ~15 minutes (± 1 minute).
    """
    logging.info(f"Starting account balance sync for chat_id {chat_id}")

    def _sync():
        base_interval = 15 * 60
        db = UserDatabase()

        while True:
            sleep_time = base_interval + random.randint(-60, 60)
            logging.debug(f"Sleeping for {sleep_time} seconds before next sync for chat_id {chat_id}")

            try:
                current_cookie = db.get_cookies(chat_id)
                if not current_cookie:
                    logging.warning(f"No cookie found for chat_id {chat_id}, skipping sync.")
                    time.sleep(sleep_time)
                    continue

                new_balance = fetch_account_balance(current_cookie)
                if new_balance is not None:
                    db.set_account_balance(chat_id, new_balance)
                    last_modified = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
                    db.set_last_modify_balance(chat_id, last_modified)
                    logging.info(f"Updated balance for chat_id {chat_id}: {new_balance} (Last modified: {last_modified})")
                else:
                    logging.warning(f"Failed to update balance for chat_id {chat_id}")

            except Exception as e:
                logging.error(f"Error in balance sync for chat_id {chat_id}: {e}")

            time.sleep(sleep_time)

    threading.Thread(target=_sync, daemon=True).start()
