# HealthOS User Data

This directory contains your personal health data. On the `main` branch, only template files are provided.

## Setup for New Users

1. **Copy Templates**: Copy the `.template` files and remove the `.template` extension:
   ```bash
   cp user_data/registry/user_profile.md.template user_data/registry/user_profile.md
   cp user_data/state/current_context.json.template user_data/state/current_context.json
   ```

2. **Fill in Your Data**: Edit the files with your personal information.

3. **Start Using**: The system will now use your personalized data.

## Directory Structure

- **registry/**: Static or slowly-changing data (profile, preferences, recipes)
- **state/**: Dynamic data (current weight, fatigue level, context)
- **logs/**: Historical data (daily journals, wearable data inbox)
- **library/**: Your customized content (recipes, workouts)

## Gitignore Note

On the `main` branch, the `.gitignore` file excludes your personal data from being committed. If you want to create your own personal branch to track your data (like the `ravi` branch example), you can:

1. Create a new branch: `git checkout -b my-health-data`
2. Edit `.gitignore` to remove the `user_data/` exclusions
3. Commit your personal files to that branch

This keeps the `main` branch clean for sharing code improvements.
