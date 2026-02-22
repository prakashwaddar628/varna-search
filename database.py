import sqlite3
import json

class DesignDB:
    def __init__(self):
        self.conn = sqlite3.connect("design_vault.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        # Store features as TEXT (JSON)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS designs 
                            (path TEXT PRIMARY KEY, data TEXT)''')
        self.conn.commit()

    def add_design(self, path, features):
        data_str = json.dumps(features)
        self.cursor.execute("INSERT OR REPLACE INTO designs VALUES (?, ?)", (path, data_str))
        self.conn.commit()

    def get_all(self):
        self.cursor.execute("SELECT path, data FROM designs")
        results = self.cursor.fetchall()
        # Convert JSON back to Dictionary
        return [(r[0], json.loads(r[1])) for r in results]