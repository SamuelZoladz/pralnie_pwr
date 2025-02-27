import logging
import threading
import random
import time
import asyncio
import subprocess
import tempfile
import os
import re
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackContext
)
from telegram.ext import filters
from dotenv import load_dotenv

load_dotenv()

# Etapy rozmowy przy logowaniu do zewnętrznego serwisu
EXTERNAL_LOGIN, EXTERNAL_PASSWORD = range(2)

# Globalne słowniki przechowujące dane użytkowników:
# user_cookies – cookies pobrane ze zewnętrznego serwisu (jako string)
# user_account_state – stan konta (pobrany z parsowania HTML) dla danego użytkownika
user_cookies = {}
user_account_state = {}


def authenticate_external(login: str, password: str, chat_id: int):
    """
    Funkcja logująca do zewnętrznego serwisu za pomocą curl.
    Wykonuje POST (używając poleceń curl) do https://pralnie.org/index.php/account/login,
    zapisuje cookies do pliku tymczasowego, następnie wykonuje GET do
    https://pralnie.org/index.php/account/index, parsuje HTML szukając fragmentu:

      <span>Stan Twojego konta</span>
      <big>Jakaś liczba</big>

    i zwraca (stan, cookies) użytkownika. Dodatkowo uruchamia osobny wątek, który
    co około 15 minut (± 1 minuta) synchronizuje stan konta.
    """
    # Utwórz tymczasowy plik na cookies
    with tempfile.NamedTemporaryFile(delete=False) as cookie_file:
        cookie_filename = cookie_file.name

    # Przygotuj polecenie curl do logowania (POST)
    cmd = [
        "curl",
        "-c", cookie_filename,
        "-b", cookie_filename,
        "-X", "POST",
        "-d", f"LoginForm[username]={login}",
        "-d", f"LoginForm[password]={password}",
        "-d", "LoginForm[rememberMe]=1",
        "-d", "yt0=Zaloguj",
        "https://pralnie.org/index.php/account/login"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        os.remove(cookie_filename)
        return None

    # Odczytaj zawartość cookies
    with open(cookie_filename, "r") as f:
        cookie_data = f.read()

    # Wykonaj natychmiastowe zapytanie GET, aby pobrać stan konta
    cmd_get = [
        "curl",
        "-b", cookie_filename,
        "https://pralnie.org/index.php/account/index"
    ]
    result_get = subprocess.run(cmd_get, capture_output=True, text=True)
    os.remove(cookie_filename)
    if result_get.returncode != 0:
        return None

    # Szukamy wzorca: <span>Stan Twojego konta</span> ... <big>Jakaś liczba</big>
    match = re.search(
        r"<span>\s*Stan Twojego konta\s*</span>\s*<big>\s*([^<]+?)\s*</big>",
        result_get.stdout
    )
    if match:
        state_number = str(match.group(1)) + ' ' + str(datetime.now())
        print(state_number)
    else:
        print("sth wrong")
        state_number = 0  # Jeśli nie znaleziono, przyjmujemy 0

    # Zapisz cookies i stan konta do globalnych słowników
    user_cookies[chat_id] = cookie_data
    user_account_state[chat_id] = state_number

    # Funkcja synchronizująca stan konta w osobnym wątku
    def sync_account_state():
        base_interval = 15 * 60  # 15 minut w sekundach
        while True:
            # Losowy odstęp ± 60 sekund
            sleep_time = base_interval + random.randint(-60, 60)
            time.sleep(sleep_time)
            # Zapisz cookies do tymczasowego pliku
            with tempfile.NamedTemporaryFile(delete=False) as temp_cookie_file:
                temp_cookie_filename = temp_cookie_file.name
                temp_cookie_file.write(cookie_data.encode())
            # Wykonaj zapytanie GET
            cmd_sync = [
                "curl",
                "-b", temp_cookie_filename,
                "https://pralnie.org/index.php/account/index"
            ]
            result_sync = subprocess.run(cmd_sync, capture_output=True, text=True)
            os.remove(temp_cookie_filename)
            if result_sync.returncode != 0:
                continue
            # Parsowanie stanu konta
            match_sync = re.search(
                r"<span>\s*Stan Twojego konta\s*</span>\s*<big>\s*([^<]+?)\s*</big>",
                result_sync.stdout
            )
            if match_sync:
                new_state = str(match_sync.group(1))
                user_account_state[chat_id] = new_state + ' ' + str(datetime.now())

    # Uruchom wątek synchronizujący (daemon)
    threading.Thread(target=sync_account_state, daemon=True).start()

    # Zwróć początkowy stan oraz cookies
    return user_account_state[chat_id], cookie_data


# Funkcje obsługujące logowanie (ConversationHandler)
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Podaj login do zewnętrznego serwisu:")
    return EXTERNAL_LOGIN


async def external_login(update: Update, context: CallbackContext) -> int:
    context.user_data["external_login"] = update.message.text.strip()
    await update.message.reply_text("Podaj hasło do zewnętrznego serwisu:")
    return EXTERNAL_PASSWORD


async def external_password(update: Update, context: CallbackContext) -> int:
    login_value = context.user_data.get("external_login")
    password_value = update.message.text.strip()
    chat_id = update.message.chat_id

    auth_result = authenticate_external(login_value, password_value, chat_id)
    if auth_result is None:
        await update.message.reply_text("Niepoprawne dane. Spróbuj jeszcze raz. Podaj login:")
        return EXTERNAL_LOGIN
    else:
        state_number, cookie_data = auth_result
        await update.message.reply_text(
            "Zalogowano w zewnętrznym serwisie!\n"
            f"Stan konta: {state_number}\n"
            "Możesz teraz korzystać z komend /stan oraz /doladuj."
        )
        return ConversationHandler.END


# Komenda /stan – wyświetla aktualny stan konta
async def stan(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id in user_account_state:
        state = user_account_state[chat_id]
        await update.message.reply_text(f"Stan Twojego konta: {state}")
    else:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")


# Komenda /doladuj – przykładowa operacja doładowania
async def doladuj(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id not in user_cookies:
        await update.message.reply_text("Nie jesteś zalogowany. Użyj /start aby się zalogować.")
        return

    cookie_data = user_cookies[chat_id]
    # Zapisz cookies do tymczasowego pliku
    with tempfile.NamedTemporaryFile(delete=False) as cookie_file:
        cookie_file.write(cookie_data.encode())
        cookie_filename = cookie_file.name

    # Przygotuj polecenie curl
    cmd = [
        "curl", "-v", "-X", "POST",
        "-b", cookie_filename,
        "-d", "top_up_id=1",
        "-d", "rules=on",
        "-d", "rodo=on",
        "-d", "yt0=Doładuj konto",
        "https://pralnie.org/index.php/topUp/createRequest"
    ]

    # Wykonaj polecenie curl w osobnym wątku
    result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)

    # Usuń tymczasowy plik cookies
    os.remove(cookie_filename)

    # Szukamy w stderr nagłówka Location
    match = re.search(r"Location:\s*(\S+)", result.stderr)
    if match:
        link = match.group(1)
        await update.message.reply_text(f"Link do doładowania: {link}")
    else:
        await update.message.reply_text("Nie udało się pobrać linka do doładowania.")


async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Anulowano proces autentykacji.")
    return ConversationHandler.END


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.WARN
    )
    os.getenv("TELEGRAM_TOKEN")
    app = Application.builder().token("").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            EXTERNAL_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, external_login)],
            EXTERNAL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, external_password)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('stan', stan))
    app.add_handler(CommandHandler('doladuj', doladuj))

    app.run_polling()


if __name__ == '__main__':
    main()
