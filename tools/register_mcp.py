#!/usr/bin/env python3
import json
import os
import sys

# Constants
MCP_CONFIG_PATH = os.path.expanduser("~/.gemini/antigravity/mcp_config.json")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOCKER_CONFIG = {
    "command": "docker",
    "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        f"{PROJECT_ROOT}:/app",
        "healthos-kitchen"
    ]
}

def register_mcp():
    print(f"🔧 Checking Antigravity MCP Config at: {MCP_CONFIG_PATH}")
    
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

    # Check structure (Antigravity generally uses 'mcpServers' or just top level keys depending on version, 
    # but based on recent usage, let's assume standard MCP format)
    # Adjusting based on user's previous 'mcpServers' vs 'servers' issue. 
    # The global config usually expects 'mcpServers'.
    
    SERVER_KEY = "healthos-kitchen"
    
    # Initialize if missing
    if "mcpServers" not in config:
        config["mcpServers"] = {}
        
    # Update/Add config
    config["mcpServers"][SERVER_KEY] = DOCKER_CONFIG
    
    try:
        with open(MCP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Successfully registered '{SERVER_KEY}' to global config.")
    except Exception as e:
        print(f"❌ Failed to write config: {e}")

if __name__ == "__main__":
    register_mcp()
