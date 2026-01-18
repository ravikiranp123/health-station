import os
import json
import sys
from pathlib import Path

# Load config to get base dicts
sys.path.append(str(Path(__file__).parent.parent))
try:
    from tools.config import USER_DATA_DIR
except ImportError:
    # Fallback if config not found
    USER_DATA_DIR = Path('user_data')

SPEC_PATH = Path('library/specs/structure_spec.json')

def load_spec():
    if not SPEC_PATH.exists():
        print(f"❌ Spec file missing at {SPEC_PATH}")
        sys.exit(1)
    with open(SPEC_PATH, 'r') as f:
        return json.load(f)

def check_directories(dirs):
    missing = []
    for d in dirs:
        path = Path(d)
        if not path.exists():
            missing.append(d)
    return missing

def check_file_existence(files_spec):
    missing = []
    for rel_path, config in files_spec.items():
        if config.get('required', False):
            path = Path(rel_path)
            if not path.exists():
                missing.append(rel_path)
    return missing

def validate_json(path, required_keys):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            return f"Missing keys: {missing_keys}"
        return None
    except json.JSONDecodeError:
        return "Invalid JSON"

def validate_markdown(path, required_headers):
    with open(path, 'r') as f:
        content = f.read()
    
    missing_headers = []
    for header in required_headers:
        # Check for "## HeaderName"
        if f"## {header}" not in content and f"# {header}" not in content:
            missing_headers.append(header)
    
    if missing_headers:
        return f"Missing Headers: {missing_headers}"
    return None

def main():
    print("🔍 health-station Integrity Check...")
    spec = load_spec()
    errors = []

    # 1. Check Directories
    missing_dirs = check_directories(spec['directories'])
    for d in missing_dirs:
        errors.append(f"❌ Missing Directory: {d}")

    # 2. Check Files
    missing_files = check_file_existence(spec['files'])
    for f in missing_files:
        errors.append(f"❌ Missing File: {f}")

    # 3. Content Validation
    for rel_path, config in spec['files'].items():
        path = Path(rel_path)
        if path.exists():
            if config['format'] == 'json':
                err = validate_json(path, config.get('required_keys', []))
                if err:
                    errors.append(f"⚠️  JSON Error in {rel_path}: {err}")
            elif config['format'] == 'markdown':
                err = validate_markdown(path, config.get('required_headers', []))
                if err:
                    errors.append(f"⚠️  Markdown Error in {rel_path}: {err}")

    if errors:
        print("\n".join(errors))
        print("\n❌ Integrity Check FAILED. Fix errors above.")
        sys.exit(1)
    else:
        print("✅ System Health: 100%. Structure is valid.")

if __name__ == "__main__":
    main()
