from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database.db import UserDatabase

db = UserDatabase()


def build_topup_keyboard() -> InlineKeyboardMarkup:
    """Builds and returns the inline keyboard for top-up amounts."""
    keyboard = [
        [InlineKeyboardButton("10 zł", callback_data="1")],
        [InlineKeyboardButton("15 zł", callback_data="2")],
        [InlineKeyboardButton("20 zł", callback_data="3")],
        [InlineKeyboardButton("30 zł", callback_data="4")],
        [InlineKeyboardButton("50 zł", callback_data="5")]
    ]
    return InlineKeyboardMarkup(keyboard)


def is_logged_in(chat_id: int) -> bool:
    """Checks if the user is logged in by verifying stored cookies."""
    return db.get_cookies(chat_id) is not None


def save_user_and_pass(chat_id: int, login: str, password: str) -> None:
    """Save user login and password to the database."""
    db.set_username(chat_id, login)
    db.set_password(chat_id, password)
