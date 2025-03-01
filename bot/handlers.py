from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CallbackContext
)

from database.db import UserDatabase
from laundry_connect.account_balance import get_transactions_sum
from laundry_connect.auth import authenticate_pralni
from laundry_connect.topup import topup_account

# Conversation stages
EXTERNAL_LOGIN, EXTERNAL_PASSWORD = range(2)
db = UserDatabase()

async def start(update: Update, context: CallbackContext) -> int:
    # Ask for login to the laundry service
    await update.message.reply_text("Podaj login do serwisu pralni:")
    return EXTERNAL_LOGIN


async def external_login(update: Update, context: CallbackContext) -> int:
    # Save the provided login in user data
    context.user_data["pralni_login"] = update.message.text.strip()
    await update.message.reply_text("Podaj hasło do serwisu pralni:")
    return EXTERNAL_PASSWORD


async def external_password(update: Update, context: CallbackContext) -> int:
    # Retrieve login and password, then attempt authentication
    login_value = context.user_data.get("pralni_login")
    password_value = update.message.text.strip()
    chat_id = update.message.chat_id

    auth_result = authenticate_pralni(login_value, password_value, chat_id)
    if auth_result is None:
        await update.message.reply_text("Niepoprawne dane. Spróbuj jeszcze raz. Podaj login:")
        return EXTERNAL_LOGIN
    else:
        db.set_username(chat_id, login_value)
        db.set_password(chat_id, password_value)
        await update.message.reply_text(
            "Zalogowano w serwisie pralni!\n"
            "Możesz teraz korzystać z komend /stan oraz /doladuj."
        )
        return ConversationHandler.END


async def stan(update: Update, context: CallbackContext) -> None:
    # Display the current account balance
    chat_id = update.message.chat_id
    if db.get_cookies(chat_id):
        current_balance = get_transactions_sum(chat_id)
        if current_balance:
            await update.message.reply_text(f"Stan Twojego konta: {current_balance}")
        else:
            await update.message.reply_text(f"Coś się zepsuło. Nie udało się pobrać stanu konta.")
    else:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")


async def doladuj(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id

    if not db.get_cookies(chat_id):
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")
        return

    keyboard = [
        [InlineKeyboardButton("10 zł", callback_data="1")],
        [InlineKeyboardButton("15 zł", callback_data="2")],
        [InlineKeyboardButton("20 zł", callback_data="3")],
        [InlineKeyboardButton("30 zł", callback_data="4")],
        [InlineKeyboardButton("50 zł", callback_data="5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Wybierz kwotę doładowania:", reply_markup=reply_markup)

async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    selected_option = query.data
    if selected_option not in ("1", "2", "3", "4", "5"):
        await query.edit_message_text("Wybrano niepoprawną opcję.")
        return

    top_up_link = topup_account(chat_id, selected_option)
    if top_up_link:
        await query.edit_message_text(f"Link do doładowania: {top_up_link}")
    else:
        await query.edit_message_text("Nie udało się pobrać linka do doładowania.")


async def cancel(update: Update, context: CallbackContext) -> int:
    # Cancel the authentication process
    await update.message.reply_text("Anulowano proces autentykacji.")
    return ConversationHandler.END
