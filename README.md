# HealthOS Architecture

**HealthOS** is a "Life Engine" that treats the human body as a production environment.

## The Team (Agents)
Agents are specialized personas invoked via slash commands.
- **System Architect (`/architect`)**: Oversees the system, resolves conflicts, and manages the file structure.
- **Nutritionist (`/nutritionist`)**: Manages input (calories, macros, hydration). Reads `registry/user_profile.md` and `state/current_context.json`.
- **Strength Coach (`/coach`)**: Manages output (workouts, activity). Adjusts volume based on `fatigue_level`.

## MCP Integration (The Kitchen API)
To enable the agents to search recipes autonomously, you must configure the **Kitchen MCP Server**.

### Option 1: Docker (Recommended)
1.  **Build:** `docker build -t healthos-kitchen -f tools/Dockerfile.mcp .`
2.  **Config:** Add this to your Agent / IDE settings `mcpServers`:
    ```json
    "kitchen-docker": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "/Users/ravi/projects/health-station:/app", "healthos-kitchen"]
    }
    ```
    *(Note: Replace path with your absolute project path).*

    ```
    *(Note: Replace path with your absolute project path).*

### Option 2: Local Python
1.  **Install:** `pip install mcp`
2.  **Config:**
    ```json
    "kitchen-local": {
      "command": "uv",
      "args": ["run", "/Users/ravi/projects/health-station/tools/kitchen_server.py"],
      "env": { "PYTHONPATH": "/Users/ravi/projects/health-station" }
    }
    ```

### Antigravity Global Config
For the Antigravity Agent to utilize these tools, you must add the config to **`~/.gemini/antigravity/mcp_config.json`**.
*   You can run `python3 tools/register_mcp.py` to attempt automatic registration.
*   *Note: Workspace-level configuration (e.g. per-repo `.vscode/mcp.json`) is supported by some IDEs but may not be fully recognized by the global Agent yet.*

## Directory Structure (The Database)

### `registry/` (Static Data)
Immutable or slowly changing data.
- `user_profile.md`: Biology, equipment, medical history.
- `preferences.md`: Taste preferences, style.

### `state/` (Dynamic Data)
The mutable "RAM" of the system.
- `current_context.json`: Weight, fatigue, current goal phase (Bulk/Cut).

### `logs/` (Immutable History)
- `journal/`: Daily logs. (Format: `YYYY-MM-DD.md` is recommended).

### `library/` (Reference Material)
- `recipes/`: Collection of healthy recipes (Markdown).
- `workouts/`: Saved routine templates.

## Mobile & Wearable Sync
**Goal:** Keep data local. No Cloud.

### 1. File Sync (Syncthing)
To log data from your phone (Camera/Voice) to HealthOS:
1.  **Start the Server**: Run `docker-compose up -d` in this directory.
2.  **Web UI**: Open `http://localhost:8384`.
3.  **App**: Install **Syncthing-Fork** (Android) or **Möbius Sync** (iOS).
4.  **Connect**: Pair devices and share `HealthOS Inbox` folder.

### 2. Wearable Data (Mi Band)
1.  **App:** Use **Gadgetbridge** (Android).
2.  **Auth:** Extract Key via `huami-token`. (See `wearable_integration_plan.md`).
3.  **Flow:** Gadgetbridge Auto-Exports DB -> Syncthing Syncs file to Mac -> Script `ingest_wearable.py` updates HealthOS.

### `knowledge_base/` (Feedback Loops)
- Stores learned lessons to prevent regression (re-injuries, failed diets).

## Workflows
**Morning Protocol**:
1. User types "Good Morning".
2. System reads yesterday's logs + current readiness.
3. Agents generate the plan for the day.
