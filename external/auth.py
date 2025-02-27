import requests

from config import PRALNIE_LOGIN_URL
from external import sync


def authenticate_pralni(login: str, password: str, chat_id: int, user_cookies: dict, user_account_balance: dict):
    """
    Authenticates with the laundry service.
    Sends a POST request to the login URL and retrieves the account balance
    from the account page. If successful, it stores the cookie data and account
    balance in the provided dictionaries and starts a background thread for synchronization.
    """
    session = requests.Session()
    data = {
        "LoginForm[username]": login,
        "LoginForm[password]": password,
        "LoginForm[rememberMe]": "1",
        "yt0": "Zaloguj"
    }
    response = session.post(PRALNIE_LOGIN_URL, data=data, allow_redirects=False)
    if response.status_code != 302:
        return None

    cookie_data = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
    # Save cookie data and account balance in the provided dictionaries
    user_cookies[chat_id] = cookie_data
    # Start the account balance synchronization thread
    sync.start_sync_account_balance(cookie_data, chat_id, user_account_balance)

    # Return cookie data
    return cookie_data
