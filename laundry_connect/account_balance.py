import urllib.parse
import re
import requests
from database.db import UserDatabase


def get_transactions_sum(chat_id: int):
    """
    This function retrieves the user's cookies, decodes the session cookie,
    extracts the user ID, fetches the transaction list, and sums the "Value" fields.
    """
    db = UserDatabase()
    cookie_data = db.get_cookies(chat_id)
    if not cookie_data:
        return None

    # Split cookies into individual key=value pairs
    cookies = {}
    for cookie in cookie_data.split(";"):
        cookie = cookie.strip()
        if "=" in cookie:
            key, value = cookie.split("=", 1)
            cookies[key] = value

    # Find the cookie that is NOT PHPSESSID (assuming it's our session cookie)
    user_cookie_key = None
    for key in cookies:
        if key != "PHPSESSID":
            user_cookie_key = key
            break

    if user_cookie_key is None:
        raise ValueError("User session cookie not found.")

    # Retrieve the encoded cookie value and perform URL decoding
    encoded_cookie = cookies[user_cookie_key]
    decoded_cookie = urllib.parse.unquote(encoded_cookie)

    # Split the hash prefix from session data – split only at the first colon
    try:
        hash_prefix, session_data = decoded_cookie.split(":", 1)
    except ValueError:
        raise ValueError("Error while splitting session data. Check the input format.")

    # Remove any numerical prefix from session data
    session_data_clean = re.sub(r"^\d+:", "", session_data, count=1)

    # Parse data in PHP session format
    matches = re.findall(
        r"i:(\d+);(?:s:(\d+):\"([^\"]*)\"|i:(\d+);|a:(\d+):\{\})",
        session_data_clean
    )

    parsed_data = {}
    for match in matches:
        key = int(match[0])
        if match[1]:  # Text value
            parsed_data[key] = match[2]
        elif match[3]:  # Integer value
            parsed_data[key] = int(match[3])
        elif match[4]:  # Empty array – treat it as an empty list
            parsed_data[key] = []

    # Determine user ID – the first element (index 0)
    user_id = parsed_data.get(0)
    if user_id is None:
        raise ValueError("Failed to extract user ID from the cookie.")

    # Fetch the transaction list for the given user ID
    url = f"https://pralnie.org/index.php/accountTransaction/getTransactionList/{user_id}"
    headers = {"Cookie": cookie_data}  # Pass the original cookies
    response = requests.get(url, headers=headers)

    # Check if the response returned an OK status
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {response.status_code}")

    try:
        transactions = response.json()
    except ValueError:
        raise ValueError("Server response is not valid JSON.")

    # Sum all "Value" fields (assuming they are numeric)
    total_sum = "{:.2f}".format(round(sum(item.get("Value", 0) for item in transactions), 2))
    return total_sum
