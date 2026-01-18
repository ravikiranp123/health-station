import sqlite3
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
from tools.config import RECIPE_DB_PATH

# Paths
SQLITE_DB_PATH = RECIPE_DB_PATH
RECIPES_LIB_DIR = ROOT_DIR / "library/recipes"

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_markdown_recipe(file_path: Path) -> dict:
    """
    Parses a markdown recipe file to extract all structured fields.
    Returns a dict with: name, bio_hack, ingredients, instructions, notes, markdown_path.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {
        "name": "",
        "kannada_name": None,
        "bio_hack": "",
        "ingredients": "",       # Now raw markdown text
        "instructions": "",      # Now raw markdown text
        "prep_notes": "",
        "markdown_path": str(file_path.relative_to(ROOT_DIR))
    }

    lines = content.split('\n')
    
    # --- PARSE TITLE (Line 1: # Name (Kannada Name)) ---
    title_match = re.match(r"#\s*(.+)", lines[0] if lines else "")
    if title_match:
        full_title = title_match.group(1).strip()
        # Check for Kannada name in parentheses, e.g. "Green Moong Cheela (ಹೆಸರು ದೋಸೆ)"
        kan_match = re.search(r"\(([^)]+)\)", full_title)
        if kan_match:
            data["kannada_name"] = kan_match.group(1).strip()
            data["name"] = full_title.split("(")[0].strip()
        else:
            data["name"] = full_title
    
    # --- PARSE KEY HACKS / STATUS / BIO-GOAL (Front Matter) ---
    # Look for lines like: **Key Hacks:** ... or **Status:** ... or **Bio-Goal:**
    key_hacks_match = re.search(r"\*\*Key Hacks?:\*\*\s*(.+)", content)
    status_match = re.search(r"\*\*Status:\*\*\s*(.+)", content)
    bio_goal_match = re.search(r"\*\*Bio-Goal:\*\*\s*(.+)", content)
    relation_match = re.search(r"\*\*Relation to Stack:\*\*\s*(.+)", content)
    
    hacks_parts = []
    if bio_goal_match:
        hacks_parts.append(f"Goal: {bio_goal_match.group(1).strip()}")
    if key_hacks_match:
        hacks_parts.append(f"Hacks: {key_hacks_match.group(1).strip()}")
    if relation_match:
        hacks_parts.append(f"Stack: {relation_match.group(1).strip()}")
    if status_match and "new entry" not in status_match.group(1).lower(): # Skip generic statuses
        hacks_parts.append(status_match.group(1).strip())
        
    data["bio_hack"] = " | ".join(hacks_parts) if hacks_parts else ""

    # --- PARSE SECTIONS ---
    # We'll use a state machine to capture content under each ## heading
    current_section = None
    section_content = []
    
    for line in lines:
        # Detect new section heading
        section_heading_match = re.match(r"##\s*(.+)", line)
        if section_heading_match:
            # Save previous section if any
            if current_section and section_content:
                process_section(data, current_section, section_content)
            # Start new section
            current_section = section_heading_match.group(1).strip().lower()
            section_content = []
        elif current_section:
            section_content.append(line)
    
    # Don't forget the last section
    if current_section and section_content:
        process_section(data, current_section, section_content)
    
    return data

def process_section(data: dict, section_name: str, lines: list):
    """
    Processes a list of lines belonging to a section and populates the data dict.
    For ingredients and instructions, we now store raw markdown to preserve nesting.
    """
    # Normalize section name
    norm_section = section_name.lower()
    
    # Join lines back to markdown, stripping only leading/trailing blank lines
    raw_content = "\n".join(lines).strip()
    
    if "ingredient" in norm_section:
        # Store raw markdown to preserve nested bullets
        data["ingredients"] = raw_content
                
    elif "method" in norm_section or "instruction" in norm_section:
        # Store raw markdown to preserve numbered list formatting
        data["instructions"] = raw_content

    elif "prep" in norm_section or "hack" in norm_section or "notes" in norm_section or "doctor" in norm_section:
        # Combine into prep_notes
        if data["prep_notes"]:
            data["prep_notes"] += "\n\n" + raw_content
        else:
            data["prep_notes"] = raw_content

def normalize_name(name: str) -> str:
    if not name:
        return ""
    return name.lower().replace(" ", "").replace("_", "").replace("-", "")

def sync_recipes():
    if not SQLITE_DB_PATH.exists():
        print("Database not found.")
        return

    print(f"Connecting to database {SQLITE_DB_PATH}...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Load all recipes
    cursor.execute("SELECT id, name, kannada_name FROM recipes")
    rows = cursor.fetchall()
    
    recipe_map = {normalize_name(row["name"]): row["id"] for row in rows if row["name"]}
    
    # Also map kannada names
    for row in rows:
        if row["kannada_name"]:
            recipe_map[normalize_name(row["kannada_name"])] = row["id"]

    # Get max integer ID
    cursor.execute("SELECT MAX(CAST(id AS INTEGER)) FROM recipes")
    max_id_row = cursor.fetchone()
    current_max_id = max_id_row[0] if max_id_row and max_id_row[0] else 0

    print(f"Scanning {RECIPES_LIB_DIR}...")
    updated_count = 0
    created_count = 0
    
    # Walk through library/recipes
    for md_file in RECIPES_LIB_DIR.rglob("*.md"):
        print(f"Processing: {md_file.name}")
        
        # Parse MD
        parsed_data = parse_markdown_recipe(md_file)
        
        if not parsed_data["instructions"] and not parsed_data["ingredients"]:
            print(f"  Warning: No parseable content in {md_file.name}")
            continue

        # Find matching recipe by name
        file_stem = md_file.stem 
        normalized_stem = normalize_name(file_stem)
        normalized_title = normalize_name(parsed_data["name"])
        
        target_id = recipe_map.get(normalized_stem) or recipe_map.get(normalized_title)
        
        if target_id:
            print(f"  Matched to ID: {target_id}. Updating...")
            cursor.execute("""
                UPDATE recipes SET 
                    instructions_json = ?, 
                    ingredients_json = ?,
                    bio_hack = ?,
                    notes = ?,
                    markdown_path = ?,
                    kannada_name = COALESCE(?, kannada_name)
                WHERE id = ?
            """, (
                parsed_data["instructions"],  # Now raw text, not JSON
                parsed_data["ingredients"],   # Now raw text, not JSON
                parsed_data["bio_hack"],
                parsed_data["prep_notes"],
                parsed_data["markdown_path"], 
                parsed_data["kannada_name"],
                target_id
            ))
            updated_count += 1
        else:
            print(f"  No match found for {md_file.name}. Creating new entry...")
            # Generate new integer ID
            current_max_id += 1
            new_id = str(current_max_id)
            
            # Determine category
            category = "uncategorized"
            parts = md_file.parts
            if "recipes" in parts:
                idx = parts.index("recipes")
                if idx + 1 < len(parts) - 1:
                    category = parts[idx + 1]
            
            name = parsed_data["name"] if parsed_data["name"] else file_stem.replace("_", " ").title()
            cursor.execute("""
            INSERT INTO recipes (
                id, name, kannada_name, category, ingredients_json, tags_json, bio_hack, instructions_json, markdown_path, status, nutrition_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id, name, parsed_data.get("kannada_name"), category,
                parsed_data["ingredients"], # Store raw markdown
                json.dumps([]), parsed_data["bio_hack"], 
                parsed_data["instructions"], # Store raw markdown
                parsed_data["markdown_path"], 
                "imported", 
                json.dumps({})
            ))
            created_count += 1
            print(f"   Created {name} ({new_id})")

    conn.commit()
    conn.close()
    
    print(f"\n--- Sync Complete ---")
    print(f"Updated: {updated_count}")
    print(f"Created: {created_count}")

if __name__ == "__main__":
    sync_recipes()
