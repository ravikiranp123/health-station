import sqlite3
import json
import os

db_path = 'registry/recipes.sqlite'

def check_ids():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM recipes")
        count = cursor.fetchone()[0]
        print(f"Total recipes: {count}")
        
        cursor.execute("SELECT id, name FROM recipes ORDER BY id LIMIT 20")
        rows = cursor.fetchall()
        print("First 20 IDs:")
        for r in rows:
            print(f"{r[0]}: {r[1]}")
            
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_ids()
