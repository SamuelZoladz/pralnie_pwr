import tempfile
import os
import re
import asyncio
import subprocess
from telegram import Update
from telegram.ext import (
    ConversationHandler, CommandHandler, MessageHandler, filters, CallbackContext
)
from external.auth import authenticate_pralni
from bot.state import user_cookies, user_account_state

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

    auth_result = authenticate_pralni(login_value, password_value, chat_id, user_cookies, user_account_state)
    if auth_result is None:
        await update.message.reply_text("Niepoprawne dane. Spróbuj jeszcze raz. Podaj login:")
        return EXTERNAL_LOGIN
    else:
        state_number, cookie_data = auth_result
        await update.message.reply_text(
            "Zalogowano w serwisie pralni!\n"
            f"Stan konta: {state_number}\n"
            "Możesz teraz korzystać z komend /stan oraz /doladuj."
        )
        return ConversationHandler.END

async def stan(update: Update, context: CallbackContext) -> None:
    # Display the current account state
    chat_id = update.message.chat_id
    if chat_id in user_account_state:
        state = user_account_state[chat_id]
        await update.message.reply_text(f"Stan Twojego konta: {state}")
    else:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")

async def doladuj(update: Update, context: CallbackContext) -> None:
    # Perform a top-up operation by sending a POST request via curl
    chat_id = update.message.chat_id
    if chat_id not in user_cookies:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")
        return

    cookie_data = user_cookies[chat_id]
    # Write cookie data to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as cookie_file:
        cookie_file.write(cookie_data.encode())
        cookie_filename = cookie_file.name

    cmd = [
        "curl", "-v", "-X", "POST",
        "-b", cookie_filename,
        "-d", "top_up_id=1",
        "-d", "rules=on",
        "-d", "rodo=on",
        "-d", "yt0=Doładuj konto",
        "https://pralnie.org/index.php/topUp/createRequest"
    ]

    # Execute the curl command in a separate thread to avoid blocking
    result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)

    os.remove(cookie_filename)

    # Search for the "Location" header in stderr to retrieve the top-up link
    match = re.search(r"Location:\s*(\S+)", result.stderr)
    if match:
        link = match.group(1)
        await update.message.reply_text(f"Link do doładowania: {link}")
    else:
        await update.message.reply_text("Nie udało się pobrać linka do doładowania.")

async def cancel(update: Update, context: CallbackContext) -> int:
    # Cancel the authentication process
    await update.message.reply_text("Anulowano proces autentykacji.")
    return ConversationHandler.END
