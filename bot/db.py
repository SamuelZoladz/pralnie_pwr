import logging
import sqlite3
import threading

class SingletonMeta(type):
    _instance = None
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        logging.debug("SingletonMeta __call__ starting")
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SingletonMeta, cls).__call__(*args, **kwargs)
        logging.debug("SingletonMeta __call__ finished")
        return cls._instance

class UserDatabase(metaclass=SingletonMeta):
    def __init__(self, db_file='users.db'):
        logging.debug("UserDatabase __init__ starting")
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.lock = threading.RLock()
        self.initialize_db()
        logging.debug("UserDatabase __init__ finished")

    def initialize_db(self):
        """Creates a users table if it does not exist."""
        logging.debug("initialize_db starting")
        with self.lock:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    cookies TEXT,
                    account_balance TEXT,
                    last_modify_balance TEXT,
                    username TEXT,
                    password TEXT
                )
            ''')
            self.conn.commit()
        logging.debug("initialize_db finished")

    def get_all_chat_ids(self):
        """Returns a list of all chat_id values in the database."""
        logging.debug("get_all_chat_ids starting")
        with self.lock:
            self.cursor.execute("SELECT chat_id FROM users")
            result = [row[0] for row in self.cursor.fetchall()]
        logging.debug("get_all_chat_ids finished")
        return result


    def get_user(self, chat_id):
        """Retrieves all the data of a user with a given chat_id."""
        logging.debug(f"get_user starting for chat_id {chat_id}")
        with self.lock:
            self.cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
        logging.debug(f"get_user finished for chat_id {chat_id}")
        return result

    def set_cookies(self, chat_id, cookies):
        """
        Sets cookies for the user with the specified chat_id.
        """
        logging.debug(f"set_cookies starting for chat_id {chat_id}")
        with self.lock:
            if self.get_user(chat_id) is None:
                self.cursor.execute("INSERT INTO users (chat_id, cookies) VALUES (?, ?)", (chat_id, cookies))
            else:
                self.cursor.execute("UPDATE users SET cookies = ? WHERE chat_id = ?", (cookies, chat_id))
            self.conn.commit()
        logging.debug(f"set_cookies finished for chat_id {chat_id}")

    def get_cookies(self, chat_id):
        """
        Gets cookies for the user with the specified chat_id.
        """
        logging.debug(f"get_cookies starting for chat_id {chat_id}")
        with self.lock:
            self.cursor.execute("SELECT cookies FROM users WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
        logging.debug(f"get_cookies finished for chat_id {chat_id}")
        return result['cookies'] if result else None

    def set_account_balance(self, chat_id, balance):
        """
        Sets the account balance for the user with the given chat_id.
        """
        logging.debug(f"set_account_balance starting for chat_id {chat_id}")
        with self.lock:
            if self.get_user(chat_id) is None:
                self.cursor.execute("INSERT INTO users (chat_id, account_balance) VALUES (?, ?)", (chat_id, balance))
            else:
                self.cursor.execute("UPDATE users SET account_balance = ? WHERE chat_id = ?", (balance, chat_id))
            self.conn.commit()
        logging.debug(f"set_account_balance finished for chat_id {chat_id}")

    def get_account_balance(self, chat_id):
        """
        Gets the account balance for a user with a given chat_id.
        """
        logging.debug(f"get_account_balance starting for chat_id {chat_id}")
        with self.lock:
            self.cursor.execute("SELECT account_balance FROM users WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
        logging.debug(f"get_account_balance finished for chat_id {chat_id}")
        return result['account_balance'] if result else None

    def set_last_modify_balance(self, chat_id, last_modify_balance):
        """
        Sets the date/time of the last balance modification for a user with a given chat_id.
        """
        logging.debug(f"set_last_modify_balance starting for chat_id {chat_id}")
        with self.lock:
            if self.get_user(chat_id) is None:
                self.cursor.execute(
                    "INSERT INTO users (chat_id, last_modify_balance) VALUES (?, ?)",
                    (chat_id, last_modify_balance)
                )
            else:
                self.cursor.execute(
                    "UPDATE users SET last_modify_balance = ? WHERE chat_id = ?",
                    (last_modify_balance, chat_id)
                )
            self.conn.commit()
        logging.debug(f"set_last_modify_balance finished for chat_id {chat_id}")

    def get_last_modify_balance(self, chat_id):
        """
        Gets the date/time of the last balance modification for a user with a given chat_id.
        """
        logging.debug(f"get_last_modify_balance starting for chat_id {chat_id}")
        with self.lock:
            self.cursor.execute("SELECT last_modify_balance FROM users WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
        logging.debug(f"get_last_modify_balance finished for chat_id {chat_id}")
        return result['last_modify_balance'] if result else None

    def set_username(self, chat_id, username):
        """
        Sets the username for the user with the given chat_id.
        """
        logging.debug(f"set_username starting for chat_id {chat_id}")
        with self.lock:
            if self.get_user(chat_id) is None:
                self.cursor.execute("INSERT INTO users (chat_id, username) VALUES (?, ?)", (chat_id, username))
                logging.info(f"Inserted new user with chat_id {chat_id} and username {username}")
            else:
                self.cursor.execute("UPDATE users SET username = ? WHERE chat_id = ?", (username, chat_id))
                logging.info(f"Updated username for chat_id {chat_id} to {username}")
            self.conn.commit()
        logging.debug(f"set_username finished for chat_id {chat_id}")

    def get_username(self, chat_id):
        """
        Gets the username for the user with the given chat_id.
        """
        logging.debug(f"get_username starting for chat_id {chat_id}")
        with self.lock:
            self.cursor.execute("SELECT username FROM users WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
        logging.debug(f"get_username finished for chat_id {chat_id}")
        return result['username'] if result else None

    def set_password(self, chat_id, password):
        """
        Sets the password for the user with the given chat_id.
        We store the password in plaintext.
        """
        logging.debug(f"set_password starting for chat_id {chat_id}")
        with self.lock:
            if self.get_user(chat_id) is None:
                self.cursor.execute("INSERT INTO users (chat_id, password) VALUES (?, ?)", (chat_id, password))
            else:
                self.cursor.execute("UPDATE users SET password = ? WHERE chat_id = ?", (password, chat_id))
            self.conn.commit()
        logging.debug(f"set_password finished for chat_id {chat_id}")

    def get_password(self, chat_id):
        """
        Gets the password for the user with the given chat_id.
        """
        logging.debug(f"get_password starting for chat_id {chat_id}")
        with self.lock:
            self.cursor.execute("SELECT password FROM users WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
        logging.debug(f"get_password finished for chat_id {chat_id}")
        return result['password'] if result else None

    def close(self):
        """Close connection to db"""
        logging.debug("close starting")
        with self.lock:
            self.conn.close()
        logging.debug("close finished")
