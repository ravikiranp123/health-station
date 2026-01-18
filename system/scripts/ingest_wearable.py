import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path

# Use centralized config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.config import INBOX_DIR, CURRENT_CONTEXT_PATH, JOURNAL_DIR

DB_PATH = str(INBOX_DIR / "Gadgetbridge")
CONTEXT_FILE = str(CURRENT_CONTEXT_PATH)
JOURNAL_DIR = str(JOURNAL_DIR)

def get_db_path():
    # Check for .sqlite or no extension
    if os.path.exists(DB_PATH + ".sqlite"):
        return DB_PATH + ".sqlite"
    if os.path.exists(DB_PATH):
        return DB_PATH
    return None

def fetch_data(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Dates
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # 1. Get Steps for Today (Simple Sum of raw intensity/steps if available, or just raw count)
    # Note: Gadgetbridge schema varies. This is a generic query for Mi Bands.
    # Usually: MI_BAND_ACTIVITY_SAMPLE table with (timestamp, raw_intensity, steps)
    try:
        # Epoch start of today
        start_ts = int(datetime(today.year, today.month, today.day).timestamp())
        
        cursor.execute(f"SELECT sum(steps) FROM MI_BAND_ACTIVITY_SAMPLE WHERE timestamp >= {start_ts}")
        steps_result = cursor.fetchone()
        steps = steps_result[0] if steps_result and steps_result[0] else 0
    except Exception as e:
        print(f"Error fetching steps: {e}")
        steps = 0

    # 2. Get Sleep for Last Night (Sleep usually spans yesterday PM to today AM)
    # We look for sleep sessions ending after yesterday 8 PM
    try:
        # Epoch yesterday 8 PM
        sleep_start_search = int(datetime(yesterday.year, yesterday.month, yesterday.day, 20, 0).timestamp())
        
        # Query for SLEEP table (timestamp_from, timestamp_to, resolution, active)
        # Note: Valid sleep usually has resolution=1 (light?) or similar. This is simplified.
        cursor.execute(f"SELECT sum(timestamp_to - timestamp_from) FROM MI_BAND_ACTIVITY_SAMPLE WHERE timestamp >= {sleep_start_search} AND raw_kind IN (112, 122)") # 112=Deep, 122=Light (Example constants, vary by device)
        
        # Alternative: Gadgetbridge specific SLEEP table doesn't always exist. 
        # Often it's calculated from raw activity. 
        # For now, we will assume a generic placeholder or manual logic if specific table missing.
        # Let's try to query a 'base' activity table if possible.
        
        # RETRYING with a more generic approach if specific table fails:
        # Just searching for 'timestamp' and assuming raw_kind for sleep
        
        # For Mi Band, raw_kind:
        # 112 = Deep Sleep
        # 122 = Light Sleep
        # 115 = REM ?
        
        cursor.execute(f"SELECT raw_kind, count(*) FROM MI_BAND_ACTIVITY_SAMPLE WHERE timestamp >= {sleep_start_search} AND raw_kind IN (112, 115, 121, 122) GROUP BY raw_kind")
        rows = cursor.fetchall()
        
        total_sleep_minutes = 0
        deep_sleep_minutes = 0
        
        for kind, count in rows:
            # Each sample is usually 1 minute (check resolution)
            total_sleep_minutes += count
            if kind == 112:
                deep_sleep_minutes += count
                
        sleep_hours = round(total_sleep_minutes / 60, 2)
        
    except Exception as e:
        print(f"Error fetching sleep: {e}")
        sleep_hours = 0
        deep_sleep_minutes = 0

    conn.close()
    return {"steps": steps, "sleep_hours": sleep_hours, "deep_sleep_mins": deep_sleep_minutes}

def update_context(data):
    try:
        with open(CONTEXT_FILE, 'r') as f:
            context = json.load(f)
        
        # Update fields
        context['last_updated'] = str(datetime.now())
        context['metrics'] = {
            "steps_today": data['steps'],
            "sleep_last_night": data['sleep_hours']
        }
        
        # Simple Logic: If sleep < 6h, Increase Fatigue
        if data['sleep_hours'] > 0 and data['sleep_hours'] < 6.0:
            context['fatigue_level'] = min(context.get('fatigue_level', 5) + 2, 10)
            context['fatigue_source'] = "Detected Low Sleep"
        
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(context, f, indent=4)
        print("Context updated.")
    except Exception as e:
        print(f"Error updating context: {e}")

def update_journal(data):
    today_str = str(date.today())
    file_path = os.path.join(JOURNAL_DIR, f"{today_str}.md")
    
    content = f"\n\n## Bio-Data Sync ({datetime.now().strftime('%H:%M')})\n"
    content += f"*   **Steps:** {data['steps']}\n"
    content += f"*   **Sleep:** {data['sleep_hours']} hours ({data['deep_sleep_mins']}m Deep)\n"
    
    try:
        with open(file_path, 'a') as f:
            f.write(content)
        print("Journal updated.")
    except Exception as e:
        print(f"Error updating journal: {e}")

if __name__ == "__main__":
    db_file = get_db_path()
    if not db_file:
        print("No Gadgetbridge DB found in logs/inbox/")
        sys.exit(1)
        
    print(f"Processing {db_file}...")
    data = fetch_data(db_file)
    print(f"Data Found: {data}")
    
    update_context(data)
    update_journal(data)
