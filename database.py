import sqlite3
import json

class DesignDB:
    def __init__(self):
        # check_same_thread=False is needed for the background scanner thread
        self.conn = sqlite3.connect("design_vault.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        # Ensure table uses 'data' column for pattern storage
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS designs 
                            (path TEXT PRIMARY KEY, data TEXT)''')
        self.conn.commit()

    def add_design(self, path, features):
        data_str = json.dumps(features)
        self.cursor.execute("INSERT OR REPLACE INTO designs VALUES (?, ?)", (path, data_str))
        self.conn.commit()

    def get_all(self):
        self.cursor.execute("SELECT path, data FROM designs")
        # Parse JSON strings back into Python lists for the AI engine
        return [(r[0], json.loads(r[1])) for r in self.cursor.fetchall()]