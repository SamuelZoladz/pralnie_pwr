import logging

import requests

from config import PRALNIE_TOPUP_URL
from database.db import UserDatabase


def topup_account(chat_id: int, topup_value: str = '1'):
    """
    Perform a top-up operation by sending a POST request.
    """
    logging.info(f"Starting top-up process for chat_id: {chat_id} with value: {topup_value}")

    db = UserDatabase()
    cookie_data = db.get_cookies(chat_id)

    if not cookie_data:
        logging.warning(f"No cookies found for chat_id: {chat_id}. Aborting top-up.")
        return None

    headers = {"Cookie": cookie_data}
    data = {
        "top_up_id": topup_value,
        "rules": "on",
        "rodo": "on",
        "yt0": "Doładuj konto"
    }

    try:
        print(data)
        print(headers)
        logging.info(f"Sending top-up request for chat_id: {chat_id}")
        response = requests.post(
            PRALNIE_TOPUP_URL,
            headers=headers,
            data=data,
            allow_redirects=False
        )

        if response.status_code >= 400:
            logging.error(f"Top-up request failed with status {response.status_code} for chat_id: {chat_id}")
            print(response.headers.get("Location"))
            return None

        top_up_link = response.headers.get("Location")
        if top_up_link:
            logging.info(f"Top-up successful for chat_id: {chat_id}. Redirect link: {top_up_link}")
        else:
            logging.warning(f"Top-up request for chat_id: {chat_id} returned no redirect link.")

        return top_up_link

    except requests.RequestException as e:
        logging.error(f"Exception occurred during top-up for chat_id: {chat_id} - {e}")
        return None
