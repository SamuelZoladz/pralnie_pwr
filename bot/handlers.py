import asyncio

import requests
from telegram import Update
from telegram.ext import (
    ConversationHandler, CallbackContext
)

from bot.state import user_cookies, user_account_balance
from external.auth import authenticate_pralni

# Conversation stages
EXTERNAL_LOGIN, EXTERNAL_PASSWORD = range(2)


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

    auth_result = authenticate_pralni(login_value, password_value, chat_id, user_cookies, user_account_balance)
    if auth_result is None:
        await update.message.reply_text("Niepoprawne dane. Spróbuj jeszcze raz. Podaj login:")
        return EXTERNAL_LOGIN
    else:
        await update.message.reply_text(
            "Zalogowano w serwisie pralni!\n"
            "Możesz teraz korzystać z komend /stan oraz /doladuj."
        )
        return ConversationHandler.END


async def stan(update: Update, context: CallbackContext) -> None:
    # Display the current account balance
    chat_id = update.message.chat_id
    if chat_id in user_cookies:
        if chat_id in user_account_balance:
            account_balance = user_account_balance[chat_id]
            await update.message.reply_text(f"Stan Twojego konta: {account_balance}")
        else:
            await update.message.reply_text(f"Trwa synchronizacja, proszę czekać")
    else:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")


async def doladuj(update: Update, context: CallbackContext) -> None:
    # Perform a top-up operation by sending a POST request
    chat_id = update.message.chat_id
    if chat_id not in user_cookies:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")
        return

    cookie_data = user_cookies[chat_id]
    headers = {"Cookie": cookie_data}
    data = {
        "top_up_id": "1",
        "rules": "on",
        "rodo": "on",
        "yt0": "Doładuj konto"
    }
    response = await asyncio.to_thread(
        requests.post,
        "https://pralnie.org/index.php/topUp/createRequest",
        headers=headers,
        data=data,
        allow_redirects=False
    )
    top_up_link = response.headers.get("Location")
    if top_up_link:
        await update.message.reply_text(f"Link do doładowania: {top_up_link}")
    else:
        await update.message.reply_text("Nie udało się pobrać linka do doładowania.")


async def cancel(update: Update, context: CallbackContext) -> int:
    # Cancel the authentication process
    await update.message.reply_text("Anulowano proces autentykacji.")
    return ConversationHandler.END
