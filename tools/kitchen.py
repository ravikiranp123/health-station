#!/usr/bin/env python3
import json
import argparse
import sys
import os
import random

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'registry', 'recipes.sqlite')

def load_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes")
        rows = cursor.fetchall()
        
        recipes = []
        for row in rows:
            d = dict(row)
            # Parse JSON fields and handle ingredients/instructions
            if d.get('tags_json'):
                try: d['tags'] = json.loads(d['tags_json'])
                except: d['tags'] = []
            
            # Map main_ingredients
            val = d.get('ingredients_json')
            if val:
                try: d['main_ingredients'] = json.loads(val)
                except: d['main_ingredients'] = val
            
            recipes.append(d)
        conn.close()
        return recipes
    except Exception as e:
        print(f"Error loading database: {e}")
        sys.exit(1)

def filter_recipes(recipes, args):
    results = recipes

    # Filter by Category
    if args.category:
        results = [r for r in results if r.get('category', '').lower() == args.category.lower()]

    # Filter by Tags (ANY match)
    if args.tag:
        search_tags = [t.lower() for t in args.tag]
        results = [r for r in results if any(t.lower() in [rt.lower() for rt in r.get('tags', [])] for t in search_tags)]

    # Filter by Ingredients
    if args.ingredient:
        search_ingredients = [i.lower() for i in args.ingredient]
        scored_results = []
        for r in results:
            # Handle both list and string
            ing_data = r.get('main_ingredients', [])
            recipe_ingredients = " ".join(ing_data).lower() if isinstance(ing_data, list) else str(ing_data).lower()
            score = sum(1 for term in search_ingredients if term in recipe_ingredients)
            if score > 0:
                scored_results.append((score, r))
        
        scored_results.sort(key=lambda x: x[0], reverse=True)
        results = [x[1] for x in scored_results]

    # Exclude logic
    if args.exclude:
        exclude_terms = [e.lower() for e in args.exclude]
        def should_exclude(r):
            ing_data = r.get('main_ingredients', [])
            ing_str = " ".join(ing_data).lower() if isinstance(ing_data, list) else str(ing_data).lower()
            name_str = r.get('name', '').lower()
            return any(e in ing_str or e in name_str for e in exclude_terms)
        results = [r for r in results if not should_exclude(r)]

    return results

def print_recipe(recipe, detailed=False):
    print(f"[{recipe['id']}] {recipe['name']}")
    print(f"    Category: {recipe.get('category', 'N/A')}")
    print(f"    Kannada: {recipe.get('kannada_name', 'N/A')}")
    print(f"    Tags: {', '.join(recipe.get('tags', []))}")
    if detailed:
        ing_data = recipe.get('main_ingredients', [])
        ing_str = ', '.join(ing_data) if isinstance(ing_data, list) else str(ing_data)
        print(f"    Ingredients: {ing_str}")
        print(f"    Bio-Hack: {recipe.get('bio_hack', 'N/A')}")
    print("-" * 40)

def main():
    parser = argparse.ArgumentParser(description="HealthOS Kitchen API")
    parser.add_argument('--category', help='Filter by Meal Category')
    parser.add_argument('--tag', action='append', help='Filter by Tag')
    parser.add_argument('--ingredient', action='append', help='Search for ingredient')
    parser.add_argument('--exclude', action='append', help='Exclude items')
    parser.add_argument('--random', action='store_true', help='Pick one random result.')
    parser.add_argument('--detailed', action='store_true', help='Show full details.')
    parser.add_argument('--limit', type=int, default=10, help='Max results to show.')

    args = parser.parse_args()
    
    all_recipes = load_db()
    results = filter_recipes(all_recipes, args)

    if args.random and results:
        results = [random.choice(results)]

    print(f"Found {len(results)} recipes matching criteria.\n")
    
    for r in results[:args.limit]:
        print_recipe(r, args.detailed)

    if len(results) == 0:
        print("No recipes found. Try broadening your search.")

if __name__ == "__main__":
    import sqlite3
    main()
