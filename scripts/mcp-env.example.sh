#!/usr/bin/env bash
# Copy this file to scripts/mcp-env.sh (gitignored) and fill in real values.
# Cursor expands ${RENDER_API_KEY} and ${GITHUB_PERSONAL_ACCESS_TOKEN} in .cursor/mcp.json
# when those variables exist in the environment used to launch Cursor.
#
#   cp scripts/mcp-env.example.sh scripts/mcp-env.sh
#   chmod +x scripts/mcp-env.sh
#   # edit scripts/mcp-env.sh, then from the same terminal:
#   source scripts/mcp-env.sh && cursor .
#
# Alternatively: set the same exports in ~/.zshrc or use Cursor Settings → MCP env.

export RENDER_API_KEY=""
export GITHUB_PERSONAL_ACCESS_TOKEN=""
