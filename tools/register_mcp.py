#!/usr/bin/env python3
"""
Register the HealthOS Kitchen MCP server with Antigravity.
Uses uv instead of Docker for simpler deployment.
"""
import json
import os
import sys

# Constants
MCP_CONFIG_PATH = os.path.expanduser("~/.gemini/antigravity/mcp_config.json")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UV_CONFIG = {
    "command": "uv",
    "args": [
        "run",
        "--directory",
        PROJECT_ROOT,
        "tools/kitchen_server.py"
    ],
    "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": PROJECT_ROOT
    }
}

def register_mcp():
    print(f"🔧 Checking Antigravity MCP Config at: {MCP_CONFIG_PATH}")
    print(f"📁 Project root: {PROJECT_ROOT}")
    
    if not os.path.exists(MCP_CONFIG_PATH):
        print(f"⚠️  Config file not found. Creating new one...")
        config = {"mcpServers": {}}
    else:
        try:
            with open(MCP_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print("❌ Error reading JSON. Aborting to avoid corrupting file.")
            sys.exit(1)

    SERVER_KEY = "healthos-kitchen"
    
    # Initialize if missing
    if "mcpServers" not in config:
        config["mcpServers"] = {}
        
    # Update/Add config
    config["mcpServers"][SERVER_KEY] = UV_CONFIG
    
    try:
        with open(MCP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Successfully registered '{SERVER_KEY}' to global config.")
        print(f"   Command: uv run --directory {PROJECT_ROOT} tools/kitchen_server.py")
        print(f"\n⚠️  Restart Antigravity to pick up the new MCP config.")
    except Exception as e:
        print(f"❌ Failed to write config: {e}")

if __name__ == "__main__":
    register_mcp()

