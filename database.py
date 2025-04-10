import sqlite3
import re
import os

class Database:
    def __init__(self, db_name, session_id):
        self.session_id = session_id
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_table(self, recreate=False):

        if recreate and os.path.exists(self.db_name):
            self.conn.close()
            os.remove(self.db_name)
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()

        self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS {self.session_id}
        (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, speaker TEXT, message TEXT)''')
        self.conn.commit()

    def insert_data(self, speaker, message):
        try:
            self.cursor.execute(f"INSERT INTO {self.session_id} (speaker, message) VALUES (?,?)", (speaker, message))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error in insert_data: {str(e)}")
            # Attempt to reconnect
            self.__exit__(None, None, None)
            self.__enter__()
            # Try once more
            self.cursor.execute(f"INSERT INTO {self.session_id} (speaker, message) VALUES (?,?)", (speaker, message))
            self.conn.commit()

    def fetch_data(self):
        self.cursor.execute(f"SELECT * FROM {self.session_id} ORDER BY timestamp ASC")
        history = self.cursor.fetchall()
        self.conn.close()
        history = [(log[0], log[1], re.sub('\n+', '\n', log[2])) for log in history]
        return history




