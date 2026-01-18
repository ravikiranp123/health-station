
import streamlit as st
import json
import os
import sqlite3
import re
from pathlib import Path
import glob
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="HealthStation Dashboard",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Constants & Paths
ROOT_DIR = Path(__file__).parent.parent
from tools.config import JOURNAL_DIR as CONFIG_JOURNAL_DIR, RECIPE_DB_PATH

JOURNAL_DIR = CONFIG_JOURNAL_DIR
SQLITE_DB_PATH = RECIPE_DB_PATH
KB_DIR = ROOT_DIR / "knowledge_base"
REGISTRY_DIR = ROOT_DIR / "registry"

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_recipes():
    """Load recipes from SQLite."""
    if not SQLITE_DB_PATH.exists():
        st.error("Database not found.")
        return []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes")
        rows = cursor.fetchall()
        conn.close()
        
        recipes = []
        for row in rows:
            d = dict(row)
            # Parse JSON fields (tags, nutrition) and handle ingredients/instructions as raw text
            for field in ['tags_json', 'nutrition_json']:
                if d.get(field):
                    try:
                        if field == 'tags_json':
                            d['tags'] = json.loads(d[field])
                        elif field == 'nutrition_json':
                            d['nutrition'] = json.loads(d[field])
                    except:
                        pass
            
            # Ingredients and Instructions are now raw markdown text
            # Try JSON parse for backward compatibility, fallback to raw string
            for field, key in [('ingredients_json', 'main_ingredients'), ('instructions_json', 'instructions')]:
                val = d.get(field)
                if val:
                    try:
                        parsed = json.loads(val)
                        d[key] = parsed  # Old JSON array format
                    except:
                        d[key] = val  # New raw markdown format
            recipes.append(d)
        return recipes
    except Exception as e:
        st.error(f"Error loading recipes: {e}")
        return []

def toggle_favorite(recipe_id, current_status):
    """Toggle favorite status in DB."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_status = 1 if not current_status else 0
        cursor.execute("UPDATE recipes SET is_favorite = ? WHERE id = ?", (new_status, recipe_id))
        conn.commit()
        conn.close()
        st.toast(f"Recipe {'favorited' if new_status else 'unfavorited'}!")
        # Rerun to update UI
    except Exception as e:
        st.error(f"Error updating favorite: {e}")

def render_recipe_detail(recipe, prev_id=None, next_id=None):
    """Render a single recipe in full detail view with enhanced styling."""
    
    # Hero section with title and favorite
    # Hero section with title and navigation
    col_nav_prev, col_title, col_nav_next, col_fav = st.columns([1, 8, 1, 2])
    
    with col_nav_prev:
        if prev_id:
            if st.button("←", key="nav_prev", help="Previous Recipe"):
                st.query_params.update({"page": "recipes", "id": prev_id})
                st.rerun()
                
    with col_title:
        st.markdown(f"## {recipe.get('name') or 'Untitled'}")
        if recipe.get('kannada_name'):
            st.markdown(f"*{recipe.get('kannada_name')}*")

    with col_nav_next:
        if next_id:
            if st.button("→", key="nav_next", help="Next Recipe"):
                st.query_params.update({"page": "recipes", "id": next_id})
                st.rerun()

    with col_fav:
        is_fav = recipe.get('is_favorite')
        fav_label = "❤️ Favorited" if is_fav else "♡ Add to Favorites"
        if st.button(fav_label, key=f"detail_fav_{recipe['id']}", width="stretch"):
            toggle_favorite(recipe['id'], is_fav)
            st.rerun()
    
    # Metadata badges row
    category = recipe.get('category', 'Other')
    bio_hack = recipe.get('bio_hack', '')
    tags = recipe.get('tags', [])
    
    # Create colorful badges using markdown
    badge_html = f"**`📁 {category}`**"
    if bio_hack:
        badge_html += f"   **`💡 {bio_hack[:50]}{'...' if len(bio_hack) > 50 else ''}`**"
    st.markdown(badge_html)
    
    # Tags as pills
    if tags:
        tag_str = "  ".join([f"`{tag}`" for tag in tags])
        st.markdown(f"🏷️ {tag_str}")
    
    st.write("")  # Spacing
    
    # Media section (Image and Video) - more prominent
    image_url = recipe.get('image_url')
    video_url = recipe.get('video_url')
    
    if image_url or video_url:
        if image_url and video_url:
            media_cols = st.columns(2)
            with media_cols[0]:
                st.image(image_url, width="stretch")
            with media_cols[1]:
                st.video(video_url)
        elif image_url:
            st.image(image_url, width="stretch")
        elif video_url:
            st.video(video_url)
        st.write("")  # Spacing
    
    # Content in styled containers
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 🥦 Ingredients")
        ingredients = recipe.get("main_ingredients", "")
        if isinstance(ingredients, list):
            for ing in ingredients:
                st.markdown(f"• {ing}")
        elif ingredients:
            st.markdown(ingredients)
        else:
            st.caption("No ingredients listed yet.")
            
    with c2:
        st.markdown("### 👩‍🍳 Instructions")
        instructions = recipe.get("instructions")
        if instructions:
            if isinstance(instructions, list):
                for idx, step in enumerate(instructions, 1):
                    st.markdown(f"**{idx}.** {step}")
            else:
                st.markdown(instructions)
        else:
            st.caption("No detailed instructions yet. This recipe needs review.")

    # Notes Section (if present)
    notes = recipe.get("notes")
    if notes:
        st.divider()
        st.markdown("### 📝 Notes & Tips")
        st.markdown(notes)

def linkify_journal(content, recipes):
    """
    Replace recipe names in journal content with markdown links to the dashboard.
    Format: [Recipe Name](/?page=recipes&id=RECIPE_ID)
    """
    # Create a map of normalized names to IDs
    # We'll check for both exact English name and Kannada name
    name_map = {}
    for r in recipes:
        if r.get('name'):
            name_map[r['name'].lower()] = r['id']
        if r.get('kannada_name'):
            name_map[r['kannada_name'].lower()] = r['id']

    # Function to replace matched name with link
    def replace_match(match):
        text = match.group(0)
        lower_text = text.lower()
        if lower_text in name_map:
            # Construct a deep link. 
            # Note: Streamlit query params usually work with ?param=val.
            # We will use this convention: ?nav=Recipe+Database&recipe_id=ID
            rid = name_map[lower_text]
            return f"[{text}](/?nav=Recipe+Database&recipe_id={rid})"
        return text

    # Simple regex to find potential recipe names (capitalized words)
    # This might be too aggressive or miss things. 
    # Better approach: Iterate over known recipe names and replace them.
    # To avoid replacing inside existing links, this is tricky.
    # Simplest safe approach: strict string replacement for known recipe names.
    
    # Sort names by length (descending) to match longest first ("Green Moong Dosa" before "Dosa")
    sorted_names = sorted(name_map.keys(), key=len, reverse=True)
    
    processed_content = content
    for name in sorted_names:
        # Case insensitive replacement, simpler than regex to avoid errors
        # Use regex with word boundaries to avoid partial matches
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        
        # We only want to replace if NOT already in a link like [name](...)
        # This is hard with simple regex. 
        # For now, let's just do a simple replacement and assume journal is plain text lists.
        # But we need to map back to original Case for the label.
        
        def sub_func(m):
            original_text = m.group(0)
            rid = name_map[name]
            return f"[{original_text}](?page=recipes&id={rid})"
            
        processed_content = pattern.sub(sub_func, processed_content)
        
    return processed_content

def main():
    # ---------------------------------------------------------
    # QUERY PARAMS HANDLER (URL-Based Navigation)
    # ---------------------------------------------------------
    # Pages: ?page=journal | recipes | kb
    # Recipe Detail: ?page=recipes&id=RECIPE_ID
    # Search: ?page=recipes&search=TERM
    # Category: ?page=recipes&category=Breakfast
    # ---------------------------------------------------------
    query_params = st.query_params
    
    # Get current page from URL, default to journal
    current_page = query_params.get("page", "journal")
    
    # Sidebar Navigation (Buttons to stay in same tab)
    st.sidebar.title("HealthStation 🌿")
    st.sidebar.markdown("### Navigation")
    if st.sidebar.button("📝 Daily Journal", width="stretch", type="primary" if current_page == "journal" else "secondary"):
        st.query_params.update({"page": "journal"})
        st.rerun()
    if st.sidebar.button("🍲 Recipe Database", width="stretch", type="primary" if current_page == "recipes" else "secondary"):
        st.query_params.clear()  # Clear all params (including id)
        st.query_params.update({"page": "recipes"})
        st.rerun()
    if st.sidebar.button("📚 Knowledge Base", width="stretch", type="primary" if current_page == "kb" else "secondary"):
        st.query_params.update({"page": "kb"})
        st.rerun()
    st.sidebar.divider()
    
    # Show current page indicator
    page_names = {"journal": "Daily Journal", "recipes": "Recipe Database", "kb": "Knowledge Base"}
    st.sidebar.caption(f"Current: **{page_names.get(current_page, 'Unknown')}**")



    # ---------------------------------------------------------
    # CSS: Mobile Optimizations
    # ---------------------------------------------------------
    st.markdown("""
        <style>
        /* Mobile: Transform table into vertical cards */
        @media (max-width: 640px) {
            /* Transform each row into a vertical card */
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                align-items: stretch !important;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px !important;
                margin-bottom: 12px !important;
                background: rgba(255,255,255,0.02);
            }
            
            /* Make each column take full width and stack */
            div[data-testid="column"] {
                width: 100% !important;
                max-width: 100% !important;
                flex: 0 0 auto !important;
                margin-bottom: 8px !important;
            }
            
            /* Hide the header row on mobile */
            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stCaptionContainer"]) {
                display: none !important;
            }
            
            /* Style checkbox row */
            div[data-testid="column"]:has(div[data-testid="stCheckbox"]) {
                order: -1; /* Move checkbox to top */
                margin-bottom: 0px !important;
            }
            
            /* Tighter padding */
            div.block-container {
                padding-left: 10px !important;
                padding-right: 10px !important;
            }
        }
        
        /* Floating Timer - Force Clickability */
        .floating-timer-container {
            position: fixed !important;
            bottom: 20px !important;
            right: 20px !important;
            z-index: 99999 !important;
            pointer-events: auto !important;
        }
        .floating-timer-container * {
            pointer-events: auto !important;
        }
        
        /* Add bottom padding so floating timer doesn't cover content */
        .block-container {
            padding-bottom: 120px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # JOURNAL SECTION (with Interactive Workout Tracking)
    # ---------------------------------------------------------
    if current_page == "journal":
        st.header("📝 Daily Journal")
        
        # Load recipes for linkification
        recipes = load_recipes()
        
        # Initialize session state for workout tracking
        if "workout_data" not in st.session_state:
            st.session_state.workout_data = {}
        
        if not JOURNAL_DIR.exists():
            st.warning(f"Journal directory not found at: {JOURNAL_DIR}")
        else:
            files = sorted(list(JOURNAL_DIR.glob("*.md")), reverse=True)
            if not files:
                st.info("No journal entries found.")
            else:
                filenames = [f.name for f in files]
                selected_file = st.sidebar.selectbox("Select Date", filenames)
                
                if selected_file:
                    file_path = JOURNAL_DIR / selected_file
                    st.subheader(f"Entry: {selected_file.replace('.md', '')}")
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Parse content into sections
                        lines = content.split("\n")
                        sections = []
                        current_section = {"type": "markdown", "content": [], "header": None, "round": None}
                        in_workout = False
                        in_table = False
                        current_round = None
                        table_data = []
                        
                        for i, line in enumerate(lines):
                            # Detect workout section start
                            if line.startswith("## Workout"):
                                in_workout = True
                                if current_section["content"]:
                                    sections.append(current_section)
                                current_section = {"type": "markdown", "content": [line], "header": None, "round": None}
                                continue
                            
                            # Detect round headers
                            if in_workout and line.startswith("### "):
                                # Save previous section/table
                                if in_table and table_data:
                                    sections.append({"type": "workout_table", "round": current_round, "data": table_data})
                                    table_data = []
                                    in_table = False
                                if current_section["content"]:
                                    sections.append(current_section)
                                
                                current_round = line.replace("###", "").strip()
                                current_section = {"type": "markdown", "content": [], "header": None, "round": current_round}
                                continue
                            
                            # Detect table start (header row with |)
                            if in_workout and "|" in line and "Exercise" in line and "Planned" in line:
                                if current_section["content"]:
                                    sections.append(current_section)
                                    current_section = {"type": "markdown", "content": [], "header": None, "round": None}
                                in_table = True
                                continue  # Skip header row
                            
                            # Skip table separator (|---|---|---|)
                            if in_table and re.match(r"^\|[-\s|]+\|$", line):
                                continue
                            
                            # Parse table rows
                            if in_table and line.startswith("|") and line.endswith("|"):
                                cells = [c.strip() for c in line.split("|")[1:-1]]
                                if len(cells) >= 3:
                                    exercise = cells[0]
                                    planned = cells[1]
                                    actual = cells[2] if len(cells) > 2 else ""
                                    notes = cells[3] if len(cells) > 3 else ""  # Optional 4th column
                                    
                                    # Check if completed (has ✓)
                                    is_completed = "✓" in actual
                                    # Extract numeric value from actual
                                    actual_num = re.search(r"\*\*(\d+)\*\*", actual)
                                    actual_value = int(actual_num.group(1)) if actual_num else 0
                                    # Check if timed
                                    is_timed = "s" in actual.lower() and ("plank" in exercise.lower() or "hold" in exercise.lower() or "45s" in planned or "30s" in actual)
                                    
                                    table_data.append({
                                        "id": f"{i}_{len(table_data)}",
                                        "exercise": exercise,
                                        "planned": planned,
                                        "actual": actual,
                                        "notes": notes,  # Add notes to data
                                        "actual_value": actual_value,
                                        "is_completed": is_completed,
                                        "is_timed": is_timed
                                    })

                                continue
                            
                            # End of table (non-table line after table started)
                            if in_table and not line.startswith("|"):
                                if table_data:
                                    sections.append({"type": "workout_table", "round": current_round, "data": table_data})
                                    table_data = []
                                in_table = False
                            
                            # Exit workout section on next ## header
                            if in_workout and line.startswith("## ") and not line.startswith("## Workout"):
                                in_workout = False
                                if in_table and table_data:
                                    sections.append({"type": "workout_table", "round": current_round, "data": table_data})
                                    table_data = []
                                    in_table = False
                            
                            # Regular markdown line
                            current_section["content"].append(line)
                        
                        # Flush remaining
                        if in_table and table_data:
                            sections.append({"type": "workout_table", "round": current_round, "data": table_data})
                        if current_section["content"]:
                            sections.append(current_section)
                        
                        # Render sections
                        has_workout = any(s["type"] == "workout_table" for s in sections)
                        

                        
                        # Track if we need to show save button
                        modified = False
                        
                        for section in sections:
                            if section["type"] == "markdown":
                                md_content = "\n".join(section["content"])
                                linked_content = linkify_journal(md_content, recipes)
                                st.markdown(linked_content)
                            
                            elif section["type"] == "workout_table":
                                round_name = section["round"]
                                st.markdown(f"#### {round_name}")
                                
                                # Sanitize round name for CSS/JS (remove colons, spaces, special chars)
                                safe_name = re.sub(r'[^a-zA-Z0-9]', '_', round_name)
                                
                                # Timer for this round
                                timer_html = f"""
                                <style>
                                    .round-timer-{safe_name} {{
                                        background: #1a1a2e;
                                        border: 1px solid #333;
                                        border-radius: 8px;
                                        padding: 8px;
                                        margin: 10px 0;
                                        display: flex;
                                        gap: 8px;
                                        align-items: center;
                                        justify-content: center;
                                    }}
                                    .timer-display-{safe_name} {{ font-size: 1.1em; font-family: monospace; color: #00ff88; min-width: 50px; text-align: center; }}
                                    .timer-btn-{safe_name} {{ padding: 4px 10px; border: none; border-radius: 5px; cursor: pointer; font-weight: 600; font-size: 0.85em; }}
                                    .timer-start-{safe_name} {{ background: #00c853; color: #1a1a2e; }}
                                    .timer-stop-{safe_name} {{ background: #ff1744; color: white; display: none; }}
                                    .timer-reset-{safe_name} {{ background: #424242; color: white; }}
                                </style>
                                <div class="round-timer-{safe_name}">
                                    <div class="timer-display-{safe_name}" id="timer-{safe_name}">00:00</div>
                                    <button class="timer-btn-{safe_name} timer-start-{safe_name}" id="start-{safe_name}" onclick="start_{safe_name}()">▶</button>
                                    <button class="timer-btn-{safe_name} timer-stop-{safe_name}" id="stop-{safe_name}" onclick="stop_{safe_name}()">⏸</button>
                                    <button class="timer-btn-{safe_name} timer-reset-{safe_name}" onclick="reset_{safe_name}()">↻</button>
                                </div>
                                <script>
                                    if (typeof timer_{safe_name}_interval === 'undefined') {{
                                        var timer_{safe_name}_interval=null, timer_{safe_name}_sec=0, timer_{safe_name}_running=false;
                                    }}
                                    function timerFormat_{safe_name}(s){{return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}}
                                    function timerUpdate_{safe_name}(){{
                                        const el = document.getElementById('timer-{safe_name}');
                                        if(el) el.textContent=timerFormat_{safe_name}(timer_{safe_name}_sec);
                                    }}
                                    function start_{safe_name}(){{
                                        if(!timer_{safe_name}_running){{
                                            timer_{safe_name}_running=true;
                                            document.getElementById('start-{safe_name}').style.display='none';
                                            document.getElementById('stop-{safe_name}').style.display='inline-block';
                                            timer_{safe_name}_interval=setInterval(()=>{{timer_{safe_name}_sec++;timerUpdate_{safe_name}();}},1000);
                                        }}
                                    }}
                                    function stop_{safe_name}(){{
                                        if(timer_{safe_name}_running){{
                                            timer_{safe_name}_running=false;
                                            clearInterval(timer_{safe_name}_interval);
                                            document.getElementById('start-{safe_name}').style.display='inline-block';
                                            document.getElementById('stop-{safe_name}').style.display='none';
                                        }}
                                    }}
                                    function reset_{safe_name}(){{stop_{safe_name}();timer_{safe_name}_sec=0;timerUpdate_{safe_name}();}}
                                </script>
                                """
                                st.components.v1.html(timer_html, height=60)
                                
                                # Create interactive table - Compact Mobile Layout
                                # Columns: Checkbox | Exercise + Target | Notes | Actual Input
                                col_done, col_details, col_notes, col_actual = st.columns([0.7, 3, 2, 1.5], vertical_alignment="center")
                                
                                # Headers
                                with col_done:
                                    st.caption("✓")
                                with col_details:
                                    st.caption("Exercise")
                                with col_notes:
                                    st.caption("Notes")
                                with col_actual:
                                    st.caption("Log")
                                
                                for row in section["data"]:
                                    ex_id = row["id"]
                                    
                                    # Initialize from parsed data if not in session state
                                    if ex_id not in st.session_state.workout_data:
                                        st.session_state.workout_data[ex_id] = {
                                            "completed": row["is_completed"],
                                            "value": row["actual_value"],
                                            "is_timed": row["is_timed"]
                                        }
                                    
                                    col_done, col_details, col_notes, col_actual = st.columns([0.7, 3, 2, 1.5], vertical_alignment="center")
                                    
                                    with col_done:
                                        new_completed = st.checkbox(
                                            "Mark Complete",
                                            key=f"chk_{ex_id}_{selected_file}",
                                            value=st.session_state.workout_data[ex_id]["completed"],
                                            label_visibility="collapsed"
                                        )
                                        if new_completed != st.session_state.workout_data[ex_id]["completed"]:
                                            st.session_state.workout_data[ex_id]["completed"] = new_completed
                                            modified = True
                                    
                                    with col_details:
                                        # Exercise Name + Target in one cell
                                        style = "~~" if st.session_state.workout_data[ex_id]["completed"] else "**"
                                        ex_name = f"{style}{row['exercise']}{style}"
                                        
                                        icon = "⏱️" if row["is_timed"] else "🎯"
                                        target_str = f"{icon} {row['planned']}"
                                        
                                        # Render exercise name + target
                                        st.markdown(f"{ex_name}  \n<span style='color:gray; font-size:0.9em'>{target_str}</span>", unsafe_allow_html=True)
                                        
                                    with col_notes:
                                        # Notes column - Dedicated
                                        if row.get('notes'):
                                            st.markdown(f"<span style='color:#888; font-size:0.85em; font-style:italic'>{row['notes']}</span>", unsafe_allow_html=True)
                                    
                                    with col_actual:
                                        max_val = 600 if row["is_timed"] else 100
                                        step = 5 if row["is_timed"] else 1
                                        new_val = st.number_input(
                                            "reps/sec",
                                            min_value=0,
                                            max_value=max_val,
                                            value=st.session_state.workout_data[ex_id]["value"],
                                            key=f"val_{ex_id}_{selected_file}",
                                            label_visibility="collapsed",
                                            step=step
                                        )
                                        if new_val != st.session_state.workout_data[ex_id]["value"]:
                                            st.session_state.workout_data[ex_id]["value"] = new_val
                                            modified = True
                                
                                st.write("")  # Spacing between rounds
                        
                        # Save button (only show if workout exists)
                        if has_workout:
                            st.divider()
                            col_save, col_info = st.columns([1, 3])
                            with col_save:
                                if st.button("💾 Save Progress", type="primary"):
                                    # Rebuild the markdown with updated values
                                    new_lines = []
                                    in_table_save = False
                                    current_round_save = None
                                    
                                    for line in lines:
                                        # Track current round
                                        if line.startswith("### "):
                                            current_round_save = line.replace("###", "").strip()
                                        
                                        # Skip table rows - we'll regenerate them
                                        if "|" in line and "Exercise" in line and "Planned" in line:
                                            in_table_save = True
                                            new_lines.append(line)  # Keep header
                                            continue
                                        
                                        if re.match(r"^\|[-\s|]+\|$", line):
                                            new_lines.append(line)  # Keep separator
                                            continue
                                        
                                        if in_table_save and line.startswith("|") and line.endswith("|"):
                                            cells = [c.strip() for c in line.split("|")[1:-1]]
                                            if len(cells) >= 3:
                                                exercise = cells[0]
                                                planned = cells[1]
                                                ex_id = f"{current_round_save}_{exercise}".replace(" ", "_")
                                                
                                                if ex_id in st.session_state.workout_data:
                                                    data = st.session_state.workout_data[ex_id]
                                                    val = data["value"]
                                                    done = data["completed"]
                                                    is_timed = data["is_timed"]
                                                    
                                                    if val > 0:
                                                        unit = "s" if is_timed else ""
                                                        check = " ✓" if done else ""
                                                        actual_str = f"**{val}**{unit}{check}"
                                                    else:
                                                        actual_str = "(Not logged)" if not done else "✓"
                                                    
                                                    new_lines.append(f"| {exercise} | {planned} | {actual_str} |")
                                                else:
                                                    new_lines.append(line)
                                            continue
                                        
                                        # End of table
                                        if in_table_save and not line.startswith("|"):
                                            in_table_save = False
                                        
                                        new_lines.append(line)
                                    
                                    # Write back
                                    with open(file_path, "w", encoding="utf-8") as f:
                                        f.write("\n".join(new_lines))
                                    
                                    st.toast("Progress saved! ✅")
                                    st.rerun()
                            
                            with col_info:
                                completed = sum(1 for k, v in st.session_state.workout_data.items() if v["completed"])
                                total = len([s for s in sections if s["type"] == "workout_table"])
                                total_exercises = sum(len(s["data"]) for s in sections if s["type"] == "workout_table")
                                st.progress(completed / total_exercises if total_exercises > 0 else 0, 
                                           text=f"{completed}/{total_exercises} exercises completed")
                        
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
                        import traceback
                        st.code(traceback.format_exc())

    # ---------------------------------------------------------
    # RECIPE SECTION
    # ---------------------------------------------------------
    elif current_page == "recipes":
        st.header("🍲 Recipe Database")
        
        recipes = load_recipes()
        if not recipes:
            st.warning("No recipes found or database missing.")
        else:
            # Get URL params for filters
            url_search = query_params.get("search", "")
            url_category = query_params.get("category", "All")
            url_id = query_params.get("id", None)
            url_favs = query_params.get("favs", "0") == "1"
            
            # Check for recipe detail view
            detail_recipe = None
            prev_id = None
            next_id = None
            
            if url_id:
                for idx, r in enumerate(recipes):
                    # Compare as strings to be safe
                    if str(r['id']) == str(url_id):
                        detail_recipe = r
                        # Calculate Prev/Next IDs
                        if idx > 0:
                            prev_id = recipes[idx - 1]['id']
                        if idx < len(recipes) - 1:
                            next_id = recipes[idx + 1]['id']
                        break
            
            # Check if we're viewing a single recipe detail
            if detail_recipe:
                # Show single recipe view with back button
                if st.button("← Back to list"):
                    st.query_params.clear()
                    st.query_params.update({"page": "recipes"})
                    st.rerun()
                render_recipe_detail(detail_recipe, prev_id, next_id)
            else:
                # Show filters only in list view (not detail view)
                col1, col2, col3 = st.columns([3, 1, 1], vertical_alignment="bottom")
                with col1:
                    search_term = st.text_input("Search", value=url_search, placeholder="Recipe name...", key="search_input")
                with col2:
                    categories = sorted(list(set(r.get("category", "Other") for r in recipes)))
                    cat_index = (["All"] + categories).index(url_category) if url_category in (["All"] + categories) else 0
                    selected_category = st.selectbox("Category", ["All"] + categories, index=cat_index)
                with col3:
                    show_favs = st.toggle("Favorites Only", value=url_favs)
                
                # Apply button to update URL
                if st.button("Apply Filters"):
                    st.query_params.update({"page": "recipes", "search": search_term, "category": selected_category, "favs": "1" if show_favs else "0"})

                # Filter Logic
                filtered_recipes = recipes
                if search_term:
                    filtered_recipes = [
                        r for r in filtered_recipes 
                        if search_term.lower() in (r.get("name") or "").lower() 
                        or search_term.lower() in (r.get("kannada_name") or "").lower()
                    ]
                if selected_category != "All":
                    filtered_recipes = [r for r in filtered_recipes if r.get("category") == selected_category]
                if show_favs:
                    filtered_recipes = [r for r in filtered_recipes if r.get("is_favorite", 0) == 1]

                st.caption(f"Showing {len(filtered_recipes)} recipes")
                # Display recipe list as cards
                for recipe in filtered_recipes:
                    recipe_name = recipe.get('name') or 'Untitled'
                    kannada_name = recipe.get('kannada_name') or ''
                    category = recipe.get('category', '')
                    bio_hack = recipe.get('bio_hack', '')
                    is_fav = recipe.get('is_favorite')
                    has_instructions = bool(recipe.get('instructions'))
                    
                    st.divider()
                    # Row 1: Title + Favorite
                    col_title, col_fav = st.columns([9, 1])
                    with col_title:
                        if st.button(f"**{recipe_name}**", key=f"title_{recipe['id']}", type="tertiary"):
                            st.query_params.update({"page": "recipes", "id": recipe['id']})
                            st.rerun()
                    with col_fav:
                        fav_btn = "❤️" if is_fav else "♡"
                        if st.button(fav_btn, key=f"fav_{recipe['id']}", help="Toggle Favorite"):
                            toggle_favorite(recipe['id'], is_fav)
                            st.rerun()
                    
                    # Row 2: Metadata line
                    meta_parts = []
                    if kannada_name:
                        meta_parts.append(f"*{kannada_name}*")
                    if category:
                        meta_parts.append(f"`{category}`")
                    if bio_hack:
                        short_hack = bio_hack[:40] + "..." if len(bio_hack) > 40 else bio_hack
                        meta_parts.append(f"💡 {short_hack}")
                    if not has_instructions:
                        meta_parts.append("⚠️ Needs review")
                    
                    if meta_parts:
                        st.caption(" • ".join(meta_parts))

    # ---------------------------------------------------------
    # KNOWLEDGE BASE SECTION
    # ---------------------------------------------------------
    elif current_page == "kb":
        st.header("📚 Knowledge Base")
        
        kb_files = list(KB_DIR.glob("*.md")) if KB_DIR.exists() else []
        registry_files = []
        if REGISTRY_DIR.exists():
            registry_files = [
                f for f in REGISTRY_DIR.glob("*.md") 
                if f.name in ["user_profile.md", "preferences.md"]
            ]
        
        all_files = sorted(kb_files + registry_files, key=lambda x: x.name)
        
        if not all_files:
            st.info("No knowledge base documents found.")
        else:
            file_map = {f.name: f for f in all_files}
            selected_doc = st.sidebar.selectbox("Select Document", list(file_map.keys()))
            
            if selected_doc:
                fpath = file_map[selected_doc]
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                st.subheader(selected_doc)
                st.divider()
                st.markdown(content)

if __name__ == "__main__":
    main()

