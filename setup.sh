#!/bin/bash

# Oracle MCP Server Setup Script
# This script sets up the development environment for the Oracle MCP Server

set -e

echo "🚀 Setting up Oracle MCP Server development environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your Oracle database connection details"
    echo "⚠️  Note: You must set DB_CONNECTION_STRING for the MCP server to work"
else
    echo "✅ .env file already exists"
fi

# Check Python environment
echo "🐍 Checking Python environment..."
uv run python --version

# Run basic tests
echo "🧪 Running basic import test..."
uv run python -c "import oracle_mcp_server; print('✅ Package imports successfully')"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Oracle database connection details"
echo "2. Test the connection: uv run oracle-mcp-server --debug"
echo "3. Configure VS Code MCP in .vscode/mcp.json (already done!)"
echo ""
echo "For VS Code integration:"
echo "1. Ensure GitHub Copilot extension is installed"
echo "2. The MCP server is configured in .vscode/mcp.json"
echo "3. Restart VS Code to activate the MCP server"
