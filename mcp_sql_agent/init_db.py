import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "app" / "demo.db"   # זה הנתיב לפי המבנה שלך
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  role TEXT NOT NULL
)
""")

cur.executemany(
  "INSERT INTO users (name, role) VALUES (?, ?)",
  [("Rachel", "admin"), ("Noa", "user"), ("Dana", "admin")]
)

conn.commit()
print("DB:", db_path)
print("Tables:", cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
print("Admins:", cur.execute("SELECT * FROM users WHERE role='admin'").fetchall())
conn.close()
