# HealthOS

**HealthOS** is a local-first "Life Engine" that treats your body as a production environment.

## TL;DR

```bash
# 1. Clone and setup
git clone https://github.com/ravikiranp123/health-station.git
cd health-station

# 2. Copy templates to create your personal data
cp user_data/registry/user_profile.md.template user_data/registry/user_profile.md
cp user_data/state/current_context.json.template user_data/state/current_context.json

# 3. Edit with your info, then use /nutritionist, /coach, /hacker commands

# 4. (Optional) Start dashboard to view stats
uv run tools/dashboard.py
# Open http://localhost:8050
```

> **Note:** Your personal data is gitignored on the main branch.
>
> **To version control your health data:**
> ```bash
> # 1. Create a new branch
> git checkout -b my-data-branch
>
> # 2. Edit .gitignore to allow user_data
> # Removing lines 231-233 in .gitignore
> sed -i '' '/user_data\//d' .gitignore  # MacOS/BSD
> # OR manual edit: remove "user_data/" from .gitignore
>
> # 3. Commit your data
> git add user_data/
> git commit -m "Add personal health data"
> ```

---

## The Team (Agents)

Agents are specialized personas invoked via slash commands:

| Command           | Agent          | Reads                                                                            | Purpose                              |
| ----------------- | -------------- | -------------------------------------------------------------------------------- | ------------------------------------ |
| `/nutritionist` | Dr. Nutrition  | `user_data/registry/user_profile.md`, `user_data/state/current_context.json` | Meal planning, macro tracking        |
| `/coach`        | Coach Iron     | `user_data/state/current_context.json`                                         | Workout planning based on fatigue    |
| `/hacker`       | Life Hacker    | `user_data/registry/`                                                          | Supplement stacks, optimizations     |
| `/chief`        | Chief of Staff | All of the above                                                                 | Daily briefings, holistic management |

## Directory Structure

```
health-station/
├── user_data/                    # 🔒 Personal (gitignored on main)
│   ├── registry/
│   │   ├── user_profile.md       # Your bio, medical history, supplements
│   │   ├── preferences.md        # Food/workout likes & dislikes
│   │   └── *.json               # Prices, product approvals
│   ├── state/
│   │   └── current_context.json  # Current weight, fatigue, goals
│   └── logs/
│       ├── journal/              # Daily logs (YYYY-MM-DD.md)
│       └── inbox/                # Wearable data staging
├── registry/                     # 📦 Shared
│   └── recipes.sqlite            # Recipe database
├── library/                      # 📚 Shared templates
│   ├── workouts/                 # Workout routines
│   └── recipes/                  # Recipe templates
└── tools/                        # 🔧 Utilities
    ├── config.py                 # Path configuration
    ├── kitchen_server.py         # Recipe MCP server
    └── dashboard.py              # Stats dashboard
```

## MCP Integration (Kitchen API)

The Kitchen MCP server lets agents search and manage recipes.

### Local Python (Recommended)

```json
{
  "healthos-kitchen": {
    "command": "uv",
    "args": ["run", "/path/to/health-station/tools/kitchen_server.py"],
    "env": {
      "PYTHONPATH": "/path/to/health-station"
    }
  }
}
```

Add to `~/.gemini/antigravity/mcp_config.json` or run `python3 tools/register_mcp.py`.

### Docker (Alternative)

```bash
docker build -t healthos-kitchen -f tools/Dockerfile.mcp .
```

## Mobile & Wearable Sync

**Goal:** Keep data local. No cloud.

### Syncthing (File Sync)

```bash
docker-compose up -d   # Start Syncthing
# Open http://localhost:8384 to configure
```

### Wearable Data (Mi Band)

1. Use **Gadgetbridge** (Android) to export data
2. Syncthing syncs to `user_data/logs/inbox/`
3. Run `python system/scripts/ingest_wearable.py` to process

## Configuration

All paths are managed by `tools/config.py`:

```python
from tools.config import USER_PROFILE_PATH, JOURNAL_DIR, RECIPE_DB_PATH
```

Override data location via environment variable:

```bash
export HEALTHOS_DATA_DIR=/custom/path/to/user_data
```

## System Integrity

To ensure your data structure is valid, run:

```bash
uv run tools/validate_integrity.py
```

This checks for missing files and verifies JSON/Markdown headers against `library/specs/structure_spec.json`.

## Branch Strategy

| Branch   | Purpose                        | Contains Personal Data? |
| -------- | ------------------------------ | ----------------------- |
| `main` | Shareable code + templates     | ❌ No                   |
| `ravi` | Personal data branch (example) | ✅ Yes                  |

## Roadmap

### ✅ Done

- [X] Agent personas (Nutritionist, Coach, Hacker, Chief)
- [X] Recipe database with MCP integration (search, add, update)
- [X] Daily journal system with workout tracking
- [X] Wearable data ingestion (Mi Band via Gadgetbridge)
- [X] Centralized config with environment variable support
- [X] Clean branch strategy (main = shareable, personal branches for data)

### 🚧 In Progress

- [ ] Syncthing integration for local-first mobile sync
- [ ] Dashboard UI for viewing stats and logs
- [ ] Voice memo transcription → journal entries

### 📋 Planned

- [ ] Photo-based meal logging (camera → nutrition estimate)
- [ ] Sleep score integration (auto-adjust workout intensity)
- [ ] Supplement timing reminders
- [ ] Weekly/monthly progress reports
- [ ] Recipe image generation
- [ ] Grocery list generator from meal plans
