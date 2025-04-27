#!/bin/bash

# Install dependencies if needed
uv pip install -e .

# Run the MCP server
python -m whatsapp_mcp.main 