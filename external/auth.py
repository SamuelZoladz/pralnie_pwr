import logging
from datetime import datetime, timedelta

import requests

from bot.db import UserDatabase
from config import PRALNIE_LOGIN_URL
from external import sync


def authenticate_pralni(login: str, password: str, chat_id: int):
    """
    Authenticates with the laundry service.
    Sends a POST request to the login URL and retrieves the account balance
    from the account page. If successful, it stores the cookie data and account
    balance in the provided dictionaries and starts a background thread for synchronization.
    """
    logging.info(f"Authenticating user {login} for chat_id {chat_id}")
    session = requests.Session()
    data = {
        "LoginForm[username]": login,
        "LoginForm[password]": password,
        "LoginForm[rememberMe]": "1",
        "yt0": "Zaloguj"
    }

    response = session.post(PRALNIE_LOGIN_URL, data=data, allow_redirects=False)

    if response.status_code != 302:
        logging.error(f"Authentication failed for user {login} with status code {response.status_code}")
        return None

    cookies = session.cookies
    cookie_data = "; ".join(f"{c.name}={c.value}" for c in cookies)
    db = UserDatabase()
    try:
        cookie_expirations = {
            c.name: datetime.utcfromtimestamp(c.expires).strftime("%Y-%m-%d %H:%M:%S UTC")
            for c in cookies if c.expires
        }
        if cookie_expirations:
            first_cookie_name, first_expiration_time = next(iter(cookie_expirations.items()))
        else:
            first_expiration_time = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d %H:%M:%S UTC")
        db.set_cookie_expirations(chat_id, first_expiration_time)
        logging.info(f"Cookie expiration times: {cookie_expirations}")
    except Exception as e:
        fallback_expiration = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d %H:%M:%S UTC")
        db.set_cookie_expirations(chat_id, fallback_expiration)
        logging.error(f"Error processing cookies: {e}. Defaulting to {fallback_expiration}")

    logging.info(f"Authentication successful for user {login}, starting sync")
    # Save cookie data and account balance
    db.set_cookies(chat_id, cookie_data)
    db.set_username(chat_id, login)
    db.set_password(chat_id, password)
    # Start the account balance synchronization thread
    sync.start_sync_account_balance(chat_id)

    # Return cookie data
    return cookie_data
