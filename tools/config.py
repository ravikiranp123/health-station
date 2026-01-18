"""
HealthOS Configuration - Centralized Path Management

This module provides configurable paths for all user data.
Supports environment variable override for flexible deployments.
"""

import os
from pathlib import Path

# Allow override via environment variable
# Default: user_data/ directory in project root
_BASE_DIR = Path(__file__).parent.parent.absolute()
USER_DATA_DIR = Path(os.getenv('HEALTHOS_DATA_DIR', _BASE_DIR / 'user_data'))

# Directory paths
REGISTRY_DIR = USER_DATA_DIR / 'registry'
STATE_DIR = USER_DATA_DIR / 'state'
LOGS_DIR = USER_DATA_DIR / 'logs'

# Recipes are shared (not personal), keep in root registry/
RECIPE_DB_PATH = _BASE_DIR / 'registry' / 'recipes.sqlite'
USER_PROFILE_PATH = REGISTRY_DIR / 'user_profile.md'
PREFERENCES_PATH = REGISTRY_DIR / 'preferences.md'
NUTRITION_MECHANICS_PATH = REGISTRY_DIR / 'nutrition_mechanics.md'
PROTEIN_PRICES_PATH = REGISTRY_DIR / 'protein_prices.json'
TRUSTIFIED_PRODUCTS_PATH = REGISTRY_DIR / 'trustified_passed_products.json'

# Specific file paths - State
CURRENT_CONTEXT_PATH = STATE_DIR / 'current_context.json'

# Specific directory paths - Logs
JOURNAL_DIR = LOGS_DIR / 'journal'
INBOX_DIR = LOGS_DIR / 'inbox'

# Ensure directories exist (create if missing)
def ensure_directories():
    """Create data directories if they don't exist."""
    for dir_path in [REGISTRY_DIR, STATE_DIR, LOGS_DIR, LIBRARY_DIR, JOURNAL_DIR, INBOX_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

# Auto-create on import (safe for read operations)
# Comment this out if you want manual control
ensure_directories()
