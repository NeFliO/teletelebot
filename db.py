import sqlite3

# Connect to or create the database file
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Create a table for users if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    registered_at TEXT
)
""")

# Save and close connection
conn.commit()
conn.close()