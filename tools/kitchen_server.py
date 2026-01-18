# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp",
# ]
# ///

from mcp.server.fastmcp import FastMCP
import json
import os
import sqlite3
import random
from typing import List, Optional, Tuple
from pathlib import Path

# Configuration - Use centralized config
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.config import RECIPE_DB_PATH

DB_PATH = str(RECIPE_DB_PATH)

# Initialize MCP Server
mcp = FastMCP("KitchenAPI")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row) -> dict:
    """Convert SQLite Row to dictionary and parse JSON fields."""
    d = dict(row)
    # Parse JSON fields back to objects
    for field in ['ingredients_json', 'tags_json', 'instructions_json', 'nutrition_json', 'nutrition', 'meta']:
        if d.get(field):
            try:
                # Map back to original JSON keys if needed
                if field == 'ingredients_json':
                    d['main_ingredients'] = json.loads(d[field])
                elif field == 'tags_json':
                    d['tags'] = json.loads(d[field])
                elif field == 'instructions_json':
                    d['instructions'] = json.loads(d[field])
                elif field == 'nutrition_json':
                    d['nutrition'] = json.loads(d[field])
                elif field == 'nutrition':
                    d['nutrition'] = json.loads(d[field])
                elif field == 'meta':
                    d['meta'] = json.loads(d[field])
                
                # Setup output keys matching original API
                # Remove internal _json suffixes from output
                if field.endswith('_json'):
                    del d[field]
            except:
                pass
    return d

@mcp.tool()
def search_recipes(category: Optional[str] = None, tags: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> str:
    """
    Search for recipes based on metadata.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM recipes WHERE 1=1"
    params = []
    
    if category and category.lower() != "all":
        query += " AND category LIKE ?"
        params.append(category)
        
    # SQLite doesn't have great array support, so we do post-filtering or LIKE hacks
    # For now, simple fetch and filter for tags/exclude is safer unless dataset is huge.
    # Given 200 recipes, fetch-all-and-filter is fine.
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    results = [row_to_dict(r) for r in rows]

    if tags:
        search_tags = [t.lower() for t in tags]
        results = [r for r in results if any(t.lower() in [rt.lower() for rt in r.get('tags', [])] for t in search_tags)]

    if exclude:
        exclude_terms = [e.lower() for e in exclude]
        results = [r for r in results if not any(e in " ".join(r.get('main_ingredients', [])).lower() for e in exclude_terms)]
        results = [r for r in results if not any(e in r.get('name', '').lower() for e in exclude_terms)]

    return json.dumps(results[:10], indent=2)

@mcp.tool()
def pantry_search(ingredients: List[str]) -> str:
    """
    Find recipes that use the provided ingredients.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes")
    rows = cursor.fetchall()
    conn.close()
    
    recipes = [row_to_dict(r) for r in rows]
    search_ingredients = [i.lower() for i in ingredients]
    
    scored_results = []
    for r in recipes:
        recipe_ingredients = " ".join(r.get('main_ingredients', [])).lower()
        score = sum(1 for term in search_ingredients if term in recipe_ingredients)
        if score > 0:
            scored_results.append((score, r))
    
    scored_results.sort(key=lambda x: x[0], reverse=True)
    results = [x[1] for x in scored_results]
    
    return json.dumps(results[:5], indent=2)

@mcp.tool()
def get_recipe(recipe_id: str) -> str:
    """
    Get full details for a specific recipe by ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.dumps(row_to_dict(row), indent=2)
    return "Recipe not found."

@mcp.tool()
def random_recipe(category: Optional[str] = None) -> str:
    """
    Get a random recipe, optionally filtered by category.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if category:
        cursor.execute("SELECT * FROM recipes WHERE category LIKE ? ORDER BY RANDOM() LIMIT 1", (category,))
    else:
        cursor.execute("SELECT * FROM recipes ORDER BY RANDOM() LIMIT 1")
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.dumps(row_to_dict(row), indent=2)
    return "No recipes found."

@mcp.tool()
def add_recipe(
    name: str, 
    category: str, 
    ingredients: str,
    instructions: str,
    tags: List[str] = [],
    bio_hack: Optional[str] = None, 
    notes: Optional[str] = None,
    kannada_name: Optional[str] = None,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None
) -> str:
    """
    Add a new recipe to the database.
    
    Standard Recipe Fields:
    - name: Recipe name (English)
    - category: Breakfast, Lunch, Dinner, Snack
    - ingredients: Raw markdown text (supports nested bullets)
    - instructions: Raw markdown text (numbered steps)
    - tags: List of tags like ["High Protein", "Keto", "Quick"]
    - bio_hack: Health optimization notes (e.g., "Milk for fluffiness")
    - notes: Additional info like nutrition notes, Dr's tips
    - kannada_name: Optional Kannada name for regional reference
    - image_url: URL to a recipe image
    - video_url: URL to a cooking video (YouTube, etc.)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate ID
    cursor.execute("SELECT MAX(CAST(id AS INTEGER)) FROM recipes")
    max_id_row = cursor.fetchone()
    current_max_id = max_id_row[0] if max_id_row and max_id_row[0] else 0
    new_id = str(current_max_id + 1)
    
    try:
        cursor.execute("""
        INSERT INTO recipes (
            id, name, kannada_name, category, ingredients_json, instructions_json, 
            tags_json, bio_hack, notes, image_url, video_url, status, nutrition_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id, name, kannada_name, category, 
            ingredients,  # Raw markdown text
            instructions,  # Raw markdown text
            json.dumps(tags), 
            bio_hack or "", 
            notes or "",
            image_url or "",
            video_url or "",
            "db_entry", 
            json.dumps({"source": "agent", "calories": 0, "protein": 0})
        ))
        conn.commit()
        conn.close()
        return f"Recipe added successfully with ID: {new_id}"
    except Exception as e:
        conn.close()
        return f"Error adding recipe: {e}"

@mcp.tool()
def update_recipe(
    recipe_id: str, 
    ingredients: Optional[str] = None,
    instructions: Optional[str] = None, 
    bio_hack: Optional[str] = None, 
    tags: Optional[List[str]] = None, 
    notes: Optional[str] = None,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    nutrition: Optional[str] = None,
    meta: Optional[str] = None
) -> str:
    """
    Update an existing recipe. Pass only the fields you want to update.
    
    Fields:
    - ingredients: Raw markdown text (supports nested bullets)
    - instructions: Raw markdown text (numbered steps)
    - bio_hack: Health optimization notes
    - tags: List of tags
    - notes: Additional info, tips
    - image_url: URL to a recipe image
    - video_url: URL to a cooking video
    - is_favorite: True/False to mark as favorite
    - nutrition: JSON string containing nutrition info
    - meta: JSON string containing metadata (prep_time, cook_time, etc.)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if ingredients is not None:
        updates.append("ingredients_json = ?")
        params.append(ingredients)
    if instructions is not None:
        updates.append("instructions_json = ?")
        params.append(instructions)
    if bio_hack is not None:
        updates.append("bio_hack = ?")
        params.append(bio_hack)
    if tags is not None:
        updates.append("tags_json = ?")
        params.append(json.dumps(tags))
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if image_url is not None:
        updates.append("image_url = ?")
        params.append(image_url)
    if video_url is not None:
        updates.append("video_url = ?")
        params.append(video_url)
    if is_favorite is not None:
        updates.append("is_favorite = ?")
        params.append(1 if is_favorite else 0)
    if nutrition is not None:
        updates.append("nutrition = ?")
        params.append(nutrition)
    if meta is not None:
        updates.append("meta = ?")
        params.append(meta)
        
    if not updates:
        conn.close()
        return "No updates provided."
    
    params.append(recipe_id)
    sql = f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(sql, params)
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return f"Recipe {recipe_id} updated."
    else:
        conn.close()
        return f"Recipe {recipe_id} not found."

@mcp.tool()
def delete_recipe(recipe_id: str) -> str:
    """
    Delete a recipe by ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return f"Recipe {recipe_id} deleted."
    else:
        conn.close()
        return f"Recipe {recipe_id} not found."

# ============================================
# INGREDIENT TOOLS
# ============================================

@mcp.tool()
def get_ingredient(name: str) -> str:
    """
    Get nutrition for an ingredient by name.
    Returns the user's default brand if available.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Try exact match first, then partial match
    cursor.execute("""
        SELECT * FROM ingredients 
        WHERE LOWER(name) = LOWER(?) 
        ORDER BY is_user_default DESC 
        LIMIT 1
    """, (name,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("""
            SELECT * FROM ingredients 
            WHERE LOWER(name) LIKE LOWER(?) 
            ORDER BY is_user_default DESC 
            LIMIT 1
        """, (f"%{name}%",))
        row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return json.dumps(dict(row), indent=2)
    return f"Ingredient '{name}' not found. Use add_ingredient to add it."

@mcp.tool()
def list_ingredients() -> str:
    """
    List all tracked ingredients with nutrition.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, brand, serving_size, protein_g, carbs_g, fat_g, calories FROM ingredients ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    
    return json.dumps([dict(r) for r in rows], indent=2)

@mcp.tool()
def add_ingredient(
    name: str,
    serving_size: str,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    calories: float,
    brand: Optional[str] = None,
    fiber_g: float = 0,
    is_user_default: bool = True,
    notes: Optional[str] = None,
    source: Optional[str] = None
) -> str:
    """
    Add a new ingredient with nutrition data.
    
    Args:
        name: Ingredient name (e.g., "Paneer")
        serving_size: Serving size description (e.g., "100g", "1 egg")
        protein_g: Protein in grams
        carbs_g: Carbohydrates in grams
        fat_g: Fat in grams
        calories: Calories
        brand: Brand name if specific (e.g., "Milky Mist")
        fiber_g: Fiber in grams (optional)
        is_user_default: Mark as user's preferred brand
        notes: Additional notes
        source: Data source (e.g., "brand_label", "NIN_IFCT_2017")
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO ingredients (name, brand, serving_size, protein_g, carbs_g, fat_g, fiber_g, calories, is_user_default, notes, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, brand, serving_size, protein_g, carbs_g, fat_g, fiber_g, calories, 1 if is_user_default else 0, notes, source))
        conn.commit()
        conn.close()
        return f"Ingredient '{name}' added successfully."
    except Exception as e:
        conn.close()
        return f"Error adding ingredient: {e}"

@mcp.tool()
def get_cooking_default(action: str) -> str:
    """
    Get default ingredient for a cooking action.
    
    Example: get_cooking_default("frying") -> {"ingredient": "Ghee", "quantity": "1 tbsp", "macros": {...}}
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cd.action, cd.ingredient_name, cd.default_quantity, cd.notes,
               i.protein_g, i.carbs_g, i.fat_g, i.calories
        FROM cooking_defaults cd
        LEFT JOIN ingredients i ON LOWER(cd.ingredient_name) = LOWER(i.name)
        WHERE LOWER(cd.action) LIKE LOWER(?)
        LIMIT 1
    """, (f"%{action}%",))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.dumps({
            "action": row["action"],
            "ingredient": row["ingredient_name"],
            "quantity": row["default_quantity"],
            "notes": row["notes"],
            "macros": {
                "protein_g": row["protein_g"],
                "carbs_g": row["carbs_g"],
                "fat_g": row["fat_g"],
                "calories": row["calories"]
            }
        }, indent=2)
    return f"No cooking default found for action '{action}'."

if __name__ == "__main__":
    mcp.run()

