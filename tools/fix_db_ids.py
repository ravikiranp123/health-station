#!/usr/bin/env python3
import sqlite3
import os
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
from tools.config import RECIPE_DB_PATH

# Paths
DB_PATH = RECIPE_DB_PATH
BACKUP_PATH = RECIPE_DB_PATH.parent / "recipes.sqlite.bak"

def fix_ids():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    # Create backup
    print(f"Creating backup at {BACKUP_PATH}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Load all recipes, sorted by category and name
    # We use COALESCE to treat NULL categories as 'other' for sorting
    print("Loading and sorting recipes...")
    cursor.execute("""
        SELECT * FROM recipes 
        ORDER BY 
            CASE 
                WHEN category = 'Breakfast' THEN 1
                WHEN category = 'Lunch' THEN 2
                WHEN category = 'Dinner' THEN 3
                WHEN category = 'Snack' THEN 4
                WHEN category = 'Breakfast/Dinner' THEN 5
                WHEN category = 'Lunch/Dinner' THEN 6
                ELSE 7
            END,
            name ASC
    """)
    rows = cursor.fetchall()

    print(f"Found {len(rows)} recipes. Starting normalization...")

    # Create a temporary table for the new data
    cursor.execute("CREATE TABLE recipes_new AS SELECT * FROM recipes WHERE 1=0")
    
    # Insert recipes with new integer IDs
    new_id = 1
    for row in rows:
        d = dict(row)
        old_id = d['id']
        d['id'] = str(new_id) # Store as string to match schema, but it's an integer
        
        columns = ', '.join(d.keys())
        placeholders = ', '.join(['?'] * len(d))
        cursor.execute(f"INSERT INTO recipes_new ({columns}) VALUES ({placeholders})", list(d.values()))
        
        print(f"  {old_id} -> {new_id}: {d['name']}")
        new_id += 1

    # Replace the old table
    cursor.execute("DROP TABLE recipes")
    cursor.execute("ALTER TABLE recipes_new RENAME TO recipes")
    
    # Re-create indices (schema from earlier)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON recipes(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON recipes(name);")

    conn.commit()
    conn.close()
    
    print("\nNormalization complete!")
    print(f"Total recipes re-indexed: {new_id - 1}")

if __name__ == "__main__":
    fix_ids()
