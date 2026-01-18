import sqlite3
import json
from tools.config import RECIPE_DB_PATH
import os

# Database path
db_path = str(RECIPE_DB_PATH)

def fetch_recipes():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Cast id to integer for correct numerical range filtering and sorting
        cursor.execute("SELECT id, name, video_url FROM recipes WHERE CAST(id AS INTEGER) BETWEEN 9 AND 18 ORDER BY CAST(id AS INTEGER)")
        rows = cursor.fetchall()
        recipes = [{"id": r[0], "name": r[1], "video_url": r[2]} for r in rows]
        print(json.dumps(recipes, indent=2))
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fetch_recipes()
