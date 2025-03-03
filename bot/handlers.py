from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from bot.utils import is_logged_in, build_topup_keyboard, save_user_and_pass
from laundry.account_balance import get_transactions_sum
from laundry.cookies import generate_session_cookies
from laundry.topup import topup_account

# Conversation stages
EXTERNAL_LOGIN, EXTERNAL_PASSWORD = range(2)


async def start(update: Update, context: CallbackContext) -> int:
    """Starts the authentication conversation by requesting the login."""
    await update.message.reply_text("Podaj login do serwisu pralni:")
    return EXTERNAL_LOGIN


async def external_login(update: Update, context: CallbackContext) -> int:
    """Stores the login and asks for the password."""
    login = update.message.text.strip()
    context.user_data["pralni_login"] = login
    await update.message.reply_text("Podaj hasło do serwisu pralni:")
    return EXTERNAL_PASSWORD


async def external_password(update: Update, context: CallbackContext) -> int:
    """
    Attempts authentication using the provided login and password.
    On success, saves credentials and notifies the user.
    On failure, restarts the login process.
    """
    login = context.user_data.get("pralni_login")
    password = update.message.text.strip()
    chat_id = update.message.chat_id

    auth_result = generate_session_cookies(login, password, chat_id)
    if auth_result is None:
        await update.message.reply_text("Niepoprawne dane. Spróbuj jeszcze raz. Podaj login:")
        return EXTERNAL_LOGIN
    save_user_and_pass(chat_id, login, password)
    await update.message.reply_text(
        "Zalogowano w serwisie pralni!\n"
        f"Aktualny stan konta: {get_transactions_sum(chat_id)}\n"
        "Możesz teraz korzystać z komend /stan oraz /doladuj."
    )
    return ConversationHandler.END


async def stan(update: Update, context: CallbackContext) -> None:
    """
    Displays the current account balance if the user is authenticated.
    Notifies the user if not logged in or if there's an error fetching the balance.
    """
    chat_id = update.message.chat_id
    if is_logged_in(chat_id):
        balance = get_transactions_sum(chat_id)
        if balance is not None:
            await update.message.reply_text(f"Stan Twojego konta: {balance}")
        else:
            await update.message.reply_text("Coś się zepsuło. Nie udało się pobrać stanu konta.")
    else:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")


async def doladuj(update: Update, context: CallbackContext) -> None:
    """
    Sends the user an inline keyboard to choose a top-up amount.
    If the user is not logged in, they are informed accordingly.
    """
    chat_id = update.message.chat_id
    if not is_logged_in(chat_id):
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")
        return

    reply_markup = build_topup_keyboard()
    await update.message.reply_text("Wybierz kwotę doładowania:", reply_markup=reply_markup)


async def button_callback(update: Update, context: CallbackContext) -> None:
    """
    Handles callback queries from the top-up selection.
    Provides the top-up link based on the selected amount or an error message if the selection is invalid.
    """
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    selected_option = query.data

    if selected_option not in map(str, range(1, 6)):
        await query.edit_message_text("Wybrano niepoprawną opcję.")
        return

    top_up_link = topup_account(chat_id, selected_option)
    if top_up_link:
        await query.edit_message_text(f"Link do doładowania: {top_up_link}")
    else:
        await query.edit_message_text("Nie udało się pobrać linka do doładowania.")


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels the authentication process."""
    await update.message.reply_text("Anulowano proces autentykacji.")
    return ConversationHandler.END
