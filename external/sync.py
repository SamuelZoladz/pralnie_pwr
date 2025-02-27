import subprocess
import tempfile
import os
import re
import time
import random
import threading
from datetime import datetime
from config import PRALNIE_ACCOUNT_URL

def start_sync_account_state(cookie_data: str, chat_id: int, user_account_state: dict):
    """
    Starts a daemon thread that synchronizes the account state
    for the given chat_id every ~15 minutes (± 1 minute).
    """
    def _sync():
        base_interval = 15 * 60  # 15 minutes in seconds
        while True:
            # Random offset ± 60 seconds
            sleep_time = base_interval + random.randint(-60, 60)
            time.sleep(sleep_time)
            # Write cookie data to a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_cookie_file:
                temp_cookie_filename = temp_cookie_file.name
                temp_cookie_file.write(cookie_data.encode())
            # Execute GET request to retrieve the updated account state
            cmd_sync = [
                "curl",
                "-b", temp_cookie_filename,
                PRALNIE_ACCOUNT_URL
            ]
            result_sync = subprocess.run(cmd_sync, capture_output=True, text=True)
            os.remove(temp_cookie_filename)
            if result_sync.returncode != 0:
                continue
            # Parse the account state from the HTML
            match_sync = re.search(
                r"<span>\s*Stan Twojego konta\s*</span>\s*<big>\s*([^<]+?)\s*</big>",
                result_sync.stdout
            )
            if match_sync:
                new_state = str(match_sync.group(1))
                user_account_state[chat_id] = new_state + ' ' + str(datetime.now())
    threading.Thread(target=_sync, daemon=True).start()
