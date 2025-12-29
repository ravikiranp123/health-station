import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'registry', 'recipes.sqlite')

print(f"BASE_DIR: {BASE_DIR}")
print(f"DB_PATH: {DB_PATH}")
print(f"Exists: {os.path.exists(DB_PATH)}")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recipes'")
        row = cursor.fetchone()
        print(f"Table 'recipes' exists: {row is not None}")
        
        cursor.execute("SELECT COUNT(*) FROM recipes")
        count = cursor.fetchone()[0]
        print(f"Recipe count: {count}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print("Database file NOT found!")
