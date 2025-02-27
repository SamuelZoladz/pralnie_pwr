import subprocess
import tempfile
import os
import re
import threading
from datetime import datetime
from external import sync
from config import PRALNIE_LOGIN_URL, PRALNIE_ACCOUNT_URL

def authenticate_pralni(login: str, password: str, chat_id: int, user_cookies: dict, user_account_state: dict):
    """
    Authenticates with the laundry service using curl.
    Sends a POST request to the login URL and retrieves the account state
    from the account page. If successful, it stores the cookie data and account
    state in the provided dictionaries and starts a background thread for synchronization.
    """
    # Create a temporary file for cookies
    with tempfile.NamedTemporaryFile(delete=False) as cookie_file:
        cookie_filename = cookie_file.name

    # Prepare curl command for login (POST)
    cmd = [
        "curl",
        "-c", cookie_filename,
        "-b", cookie_filename,
        "-X", "POST",
        "-d", f"LoginForm[username]={login}",
        "-d", f"LoginForm[password]={password}",
        "-d", "LoginForm[rememberMe]=1",
        "-d", "yt0=Zaloguj",
        PRALNIE_LOGIN_URL
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        os.remove(cookie_filename)
        return None

    # Read the cookie data
    with open(cookie_filename, "r") as f:
        cookie_data = f.read()

    # Execute a GET request to retrieve the account state
    cmd_get = [
        "curl",
        "-b", cookie_filename,
        PRALNIE_ACCOUNT_URL
    ]
    result_get = subprocess.run(cmd_get, capture_output=True, text=True)
    os.remove(cookie_filename)
    if result_get.returncode != 0:
        return None

    # Parse HTML for account state: <span>Stan Twojego konta</span> ... <big>liczba</big>
    match = re.search(
        r"<span>\s*Stan Twojego konta\s*</span>\s*<big>\s*([^<]+?)\s*</big>",
        result_get.stdout
    )
    if match:
        state_number = str(match.group(1)) + ' ' + str(datetime.now())
        print(state_number)
    else:
        print("error")
        state_number = "0"

    # Save cookie data and account state in the provided dictionaries
    user_cookies[chat_id] = cookie_data
    user_account_state[chat_id] = state_number

    # Start the account state synchronization thread
    sync.start_sync_account_state(cookie_data, chat_id, user_account_state)

    # Return the initial account state and cookie data
    return user_account_state[chat_id], cookie_data
