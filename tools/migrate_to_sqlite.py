
import sqlite3
import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
from tools.config import REGISTRY_DIR

JSON_DB_PATH = REGISTRY_DIR / "recipe_db.json"
SQLITE_DB_PATH = REGISTRY_DIR / "recipes.db"

def init_db(cursor):
    """Create the recipes table."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        kannada_name TEXT,
        category TEXT,
        bio_hack TEXT,
        status TEXT,
        markdown_path TEXT,
        ingredients_json TEXT, -- List of strings
        tags_json TEXT,        -- List of strings
        instructions_json TEXT,-- List of strings
        nutrition_json TEXT    -- Dictionary
    )
    """)
    # Create simple indices for search
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON recipes(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON recipes(name);")

def migrate():
    print(f"Reading JSON from {JSON_DB_PATH}...")
    if not JSON_DB_PATH.exists():
        print("JSON DB not found. Exiting.")
        return

    with open(JSON_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        json_recipes = data.get("recipes", [])

    print(f"Found {len(json_recipes)} recipes. Connecting to SQLite {SQLITE_DB_PATH}...")
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    init_db(cursor)
    
    inserted_count = 0
    for r in json_recipes:
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO recipes (
                id, name, kannada_name, category, bio_hack, status, markdown_path,
                ingredients_json, tags_json, instructions_json, nutrition_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("id"),
                r.get("name"),
                r.get("kannada_name"),
                r.get("category"),
                r.get("bio_hack"),
                r.get("status"),
                r.get("markdown_path"),
                json.dumps(r.get("main_ingredients", [])), # Map main_ingredients to ingredients_json
                json.dumps(r.get("tags", [])),
                json.dumps(r.get("instructions", [])),
                json.dumps(r.get("nutrition", {}))
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting recipe {r.get('id')}: {e}")

    conn.commit()
    conn.close()
    
    print(f"Migration complete. Inserted {inserted_count} recipes.")

if __name__ == "__main__":
    migrate()
