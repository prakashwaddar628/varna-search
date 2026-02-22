import sqlite3

class DesignDB:
    def __init__(self):
        # check_same_thread=False is CRITICAL for multi-threaded desktop apps
        self.conn = sqlite3.connect("design_vault.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS designs 
                            (path TEXT PRIMARY KEY, hash TEXT)''')
        self.conn.commit()

    def add_design(self, path, img_hash):
        try:
            self.cursor.execute("INSERT OR REPLACE INTO designs VALUES (?, ?)", (path, img_hash))
            self.conn.commit()
        except Exception as e:
            print(f"Database Error: {e}")

    def get_all(self):
        self.cursor.execute("SELECT path, hash FROM designs")
        return self.cursor.fetchall()