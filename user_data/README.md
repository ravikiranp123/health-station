# HealthOS User Data

This directory contains your personal health data.

## Setup for New Users

```bash
# Copy templates and fill with your info
cp registry/user_profile.md.template registry/user_profile.md
cp state/current_context.json.template state/current_context.json

# Edit with your personal data
# Then the agents will read from these files
```

## Structure

| Directory | Purpose | Examples |
|-----------|---------|----------|
| `registry/` | Static personal info | Profile, preferences, product approvals |
| `state/` | Current metrics | Weight, fatigue level, goals |
| `logs/journal/` | Daily entries | `2026-01-18.md` |
| `logs/inbox/` | Wearable imports | Gadgetbridge exports |

## Tracking Your Data in Git

On the `main` branch, this directory is **gitignored** (except templates).

To version control your personal data:

```bash
# Create your own branch
git checkout -b my-health-data

# Edit .gitignore - remove the user_data exclusions at the bottom
# Then:
git add user_data/
git commit -m "add: my personal data"
```

## Files Overview

### registry/
- `user_profile.md` - Your bio, medical history, supplement stack
- `preferences.md` - Food/exercise likes & dislikes  
- `nutrition_mechanics.md` - Educational reference material
- `*.json` - Prices, product approvals

### state/
- `current_context.json` - Current weight, body fat %, fatigue level, goals

### logs/journal/
- Daily logs in `YYYY-MM-DD.md` format
- Contains: Meals, workouts, supplements, notes
