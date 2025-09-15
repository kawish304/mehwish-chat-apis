import sqlite3

# Database create / connect
conn = sqlite3.connect('api_keys.db')
c = conn.cursor()

# Table create
c.execute('''
CREATE TABLE IF NOT EXISTS keys (
    user_id TEXT PRIMARY KEY,
    api_key TEXT
)
''')

conn.commit()
conn.close()

print("✅ Database aur table create ho gaya!")
