import sqlite3

DB_FILE = "api_keys.db"

def create_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE,
            user TEXT,
            plan TEXT,
            usage INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_api_key(key, user, plan="free"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO api_keys (key, user, plan) VALUES (?, ?, ?)", (key, user, plan))
    conn.commit()
    conn.close()
