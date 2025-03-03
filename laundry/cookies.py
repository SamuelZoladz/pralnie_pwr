import logging
import random
import time
from datetime import datetime, timedelta, timezone

import requests

from config import PRALNIE_LOGIN_URL
from database.db import UserDatabase


def generate_session_cookies(login: str, password: str, chat_id: int):
    """
    Generates and stores session cookies for the laundry service.
    Sends a POST request to authenticate the user, extracts session cookies upon success,
    and saves them along with their expiration times in the database.
    """
    logging.info(f"Generating session cookies for user {login} (chat_id: {chat_id})")
    session = requests.Session()
    data = {
        "LoginForm[username]": login,
        "LoginForm[password]": password,
        "LoginForm[rememberMe]": "1",
        "yt0": "Zaloguj"
    }

    response = session.post(PRALNIE_LOGIN_URL, data=data, allow_redirects=False)

    if response.status_code != 302:
        logging.error(f"Failed to obtain session cookies for user {login}. Status code: {response.status_code}")
        return None

    cookies = session.cookies
    cookie_data = "; ".join(f"{c.name}={c.value}" for c in cookies)
    db = UserDatabase()

    try:
        cookie_expirations = {
            c.name: datetime.utcfromtimestamp(c.expires).strftime("%Y-%m-%d %H:%M:%S UTC")
            for c in cookies if c.expires
        }
        expiration_time = (
            next(iter(cookie_expirations.values()),
                 (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d %H:%M:%S UTC"))
        )
        db.set_cookie_expirations(chat_id, expiration_time)
        logging.info(f"Stored cookie expiration times: {cookie_expirations}")
    except Exception as e:
        fallback_expiration = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d %H:%M:%S UTC")
        db.set_cookie_expirations(chat_id, fallback_expiration)
        logging.error(f"Error processing cookies: {e}. Using default expiration: {fallback_expiration}")

    logging.info(f"Session cookies successfully generated for user {login}.")
    db.set_cookies(chat_id, cookie_data)

    return cookie_data


def refresh_cookies(days_before=5):
    """
    Checks all users, and if the cookie expiration time is <= days_before,
    calls the function to generate new cookies.
    Adds a delay of about 10 minutes +/- a few seconds between each refresh.
    """
    logging.info("Starting cookie refresh")
    db = UserDatabase()
    users = db.get_users_data()
    now = datetime.now(timezone.utc)
    for user in users:
        cookie_expiration = user['cookie_expirations']

        if cookie_expiration.tzinfo is None:
            cookie_expiration = cookie_expiration.replace(tzinfo=timezone.utc)

        time_to_expiration = cookie_expiration - now
        if time_to_expiration <= timedelta(days=days_before):
            logging.info(f"Refreshing cookies for chat_id {user['chat_id']} (expires in {time_to_expiration})")
            if not generate_session_cookies(user['username'], user['password'], user['chat_id']):
                logging.error(f"Error refreshing cookies for chat_id {user['chat_id']}.")
            delay = 10 * 60 + random.randint(-60, 60)
            logging.info(f"Waiting {delay} seconds before the next refresh")
            time.sleep(delay)
    logging.info("Cookie refresh completed")


def refresh_cookies_daemon(days_before=5):
    """
    Runs refresh_cookies once a day indefinitely.
    """
    while True:
        refresh_cookies(days_before)
        logging.info("Daily check complete. Waiting 24 hours until the next check.")
        time.sleep(86400)
