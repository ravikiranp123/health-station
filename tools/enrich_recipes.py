import sqlite3
import json
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'registry', 'recipes.sqlite')

def get_recipes_to_enrich():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Find recipes where nutrition or instructions or ingredients are missing/incomplete
    # For now, let's just get all of them and we can filter in the main loop
    cursor.execute("SELECT id, name FROM recipes")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_recipe_data(recipe_id, data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if 'ingredients' in data:
        updates.append("ingredients_json = ?")
        params.append(data['ingredients'])
    if 'instructions' in data:
        updates.append("instructions_json = ?")
        params.append(json.dumps(data['instructions']))
    if 'nutrition' in data:
        updates.append("nutrition = ?")
        params.append(json.dumps(data['nutrition']))
    if 'meta' in data:
        updates.append("meta = ?")
        params.append(json.dumps(data['meta']))
    if 'image_url' in data:
        updates.append("image_url = ?")
        params.append(data['image_url'])
    if 'video_url' in data:
        updates.append("video_url = ?")
        params.append(data['video_url'])
        
    if not updates:
        conn.close()
        return
        
    params.append(recipe_id)
    sql = f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(sql, params)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    recipes = get_recipes_to_enrich()
    print(f"Found {len(recipes)} recipes to process.")
    # This script will be driven by the agent iteratively
