# Oracle MCP Server

Oracle Database MCP Server for GitHub Copilot Agent Mode

## Table of Contents

- [Overview](#overview)
- [Quick Setup](#quick-setup)
- [Docker Setup for Testing](#docker-setup-for-testing) 🐳
- [VS Code Integration](#vs-code-integration)
- [Configuration](#configuration)
- [Available Tools](#available-tools)
- [Documentation](#documentation)

## Overview

This Model Context Protocol (MCP) server provides comprehensive Oracle Database interaction capabilities, optimized for use with GitHub Copilot's agentic workflows.

### Features

- **Safe Query Execution** - Execute SELECT queries with built-in safety controls
- **Schema Inspection** - Browse database tables, views, procedures, and functions
- **Performance Analysis** - Get execution plans and query performance metrics
- **Data Export** - Export query results in JSON and CSV formats
- **Security Controls** - Whitelist tables/columns and enforce read-only operations

## Documentation

📚 **Setup Guides:**
- [Docker Example Setup](docker-example/README.md) - Complete Oracle database in Docker with sample data
- [Complete Setup Guide](docs/SETUP_GUIDE.md) - Step-by-step instructions for any Oracle database
- [Quick Reference](docs/QUICK_REFERENCE.md) - Credentials, commands, and troubleshooting

🐳 **New to Oracle?** Start with the [Docker Example](docker-example/) to get running in minutes!

## Quick Setup

### Prerequisites

- Python 3.10+ 
- [UV package manager](https://docs.astral.sh/uv/)
- Oracle Database access
- Oracle Instant Client (for advanced features)

### Installation

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd oracle-mcp-server
   ./setup.sh
   ```

2. **Configure database connection:**
   ```bash
   cp .env.example .env
   # Edit .env with your Oracle database details
   ```

3. **Test the connection:**
   ```bash
   uv run oracle-mcp-server --debug
   ```

4. **Set up VS Code integration:**
   See the [VS Code Integration](#vs-code-integration) section below for detailed setup instructions.

## Docker Setup for Testing

🐳 **New to Oracle?** Get a complete test environment running in minutes!

We provide a ready-to-use Docker setup with Oracle Database XE and sample data. Perfect for:
- Testing the MCP server
- Learning Oracle database interactions  
- Development and prototyping

### Quick Start
```bash
# Start Oracle database with sample data
cd docker-example
docker-compose up -d

# Configure MCP server
cp .env.docker ../.env

# Test the setup
cd .. && uv run oracle-mcp-server --version
```

### What You Get
- **Oracle Database XE 21c** running in Docker
- **Sample database** with employees and departments tables
- **Test user** (`testuser/TestUser123!`) with appropriate permissions
- **Ready-to-use connection** string for the MCP server

📖 **[Complete Docker Setup Guide →](docker-example/README.md)**

The Docker example includes detailed instructions, troubleshooting, sample queries, and management commands.

## VS Code Integration

### Prerequisites

1. **Install VS Code extensions:**
   - [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) - Required for MCP integration
   - [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) - Recommended for development

### Setup Steps

1. **Complete the basic setup** (see Quick Setup section above)

2. **Configure environment variables:**
   - Ensure your `.env` file has the correct `DB_CONNECTION_STRING`
   - VS Code will automatically load environment variables from `.env`

3. **MCP Configuration:**
   The project includes a pre-configured `.vscode/mcp.json` file:
   ```json
   {
     "servers": {
       "oracle-database": {
         "type": "stdio",
         "command": "uv",
         "args": ["run", "oracle-mcp-server"],
         "env": {
           "DB_CONNECTION_STRING": "${env:DB_CONNECTION_STRING}"
         }
       }
     }
   }
   ```

4. **Activate the MCP server:**
   - Open this project folder in VS Code
   - Restart VS Code to load the MCP configuration
   - The Oracle MCP server will start automatically when GitHub Copilot needs it

### Using the MCP Server

Once configured, you can interact with your Oracle database through GitHub Copilot:

1. **Ask database questions:**
   - "Show me all tables in the database"
   - "Describe the EMPLOYEES table structure" 
   - "What are the most recent orders?"

2. **Query assistance:**
   - "Generate a query to find all customers from California"
   - "Explain this query's execution plan"
   - "Export the results as CSV"

3. **Schema exploration:**
   - "What views are available?"
   - "Show me sample data from the PRODUCTS table"
   - "List all stored procedures"

### Troubleshooting VS Code Integration

**MCP server not starting:**
- Check VS Code's Output panel → "GitHub Copilot Chat" for error messages
- Verify `.env` file exists and has correct `DB_CONNECTION_STRING`
- Ensure `uv` is installed and available in PATH
- Try restarting VS Code completely

**Connection issues:**
- Test connection manually: `uv run oracle-mcp-server --debug`
- Check Oracle database is accessible
- Verify credentials in `.env` file

**No database responses:**
- Ensure GitHub Copilot extension is activated
- Check that `.vscode/mcp.json` exists in the workspace
- Verify environment variables are loading (check VS Code terminal: `echo $DB_CONNECTION_STRING`)

### Development with VS Code

The project includes VS Code-specific configurations:

- **Python interpreter:** Automatically uses the UV virtual environment
- **File associations:** SQL files are properly recognized
- **GitHub Copilot:** Enabled for Python and SQL files
- **Debugging:** Use F5 to debug the MCP server directly

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DB_CONNECTION_STRING` | Oracle connection string | *Required* | `oracle+oracledb://hr:password@localhost:1521/?service_name=XEPDB1` |
| `TABLE_WHITE_LIST` | Comma-separated list of allowed tables | All tables | `EMPLOYEES,DEPARTMENTS` |
| `COLUMN_WHITE_LIST` | Comma-separated list of allowed columns | All columns | `EMPLOYEES.ID,EMPLOYEES.NAME` |
| `QUERY_LIMIT_SIZE` | Maximum rows returned per query | `100` | `500` |
| `MAX_ROWS_EXPORT` | Maximum rows for export operations | `10000` | `50000` |
| `DEBUG` | Enable debug logging | `False` | `True` |

### Connection String Examples

```bash
# Docker test database (from this project's setup)
DB_CONNECTION_STRING="testuser/TestUser123!@localhost:1521/testdb"

# Local Oracle XE (traditional format)
DB_CONNECTION_STRING="oracle+oracledb://system:password@localhost:1521/?service_name=XE"

# Oracle Cloud Autonomous Database
DB_CONNECTION_STRING="oracle+oracledb://admin:password@hostname:1522/?service_name=your_service_tls&ssl_context=true"

# Production with connection pooling
DB_CONNECTION_STRING="oracle+oracledb://app_user:password@db.company.com:1521/?service_name=PROD&pool_size=10"
```

**Note:** The MCP server supports two connection string formats:
- **Simple format:** `username/password@host:port/service_name` (recommended for Docker setup)
- **URL format:** `oracle+oracledb://username:password@host:port/?service_name=service_name` (for compatibility)

## Available Tools

When integrated with GitHub Copilot, the following tools are available:

- `execute_query` - Execute SELECT, DESCRIBE, or EXPLAIN PLAN statements
- `describe_table` - Get detailed table schema information
- `list_tables` - Browse all database tables with metadata
- `list_views` - Browse all database views
- `list_procedures` - Browse stored procedures, functions, and packages
- `explain_query` - Analyze query execution plans for performance tuning
- `generate_sample_queries` - Generate example queries for table exploration
- `export_query_results` - Export data in JSON or CSV format

## Development

### Running Tests
```bash
uv run pytest tests/
```

### Code Formatting
```bash
uv run black src/ tests/
uv run isort src/ tests/
```

### Type Checking
```bash
uv run mypy src/
```

### Development Server
```bash
# Debug mode
uv run oracle-mcp-server --debug

# Use VS Code debugger with F5 or Ctrl+F5
```

## Security Features

- **Read-only operations** - Only SELECT, DESCRIBE, and EXPLAIN PLAN are allowed
- **SQL injection prevention** - Basic keyword filtering and parameterized queries
- **Row limiting** - Automatic ROWNUM restrictions to prevent resource exhaustion
- **Table/column whitelisting** - Restrict access to specific database objects
- **Connection pooling** - Efficient resource management

## Troubleshooting

### Common Issues

1. **Connection failures:**
   - Verify Oracle database is running
   - Check connection string format
   - Ensure Oracle Instant Client is installed (if needed)

2. **Permission errors:**
   - Verify database user has SELECT privileges
   - Check access to system views (ALL_TABLES, ALL_TAB_COLUMNS, etc.)

3. **MCP integration issues:**
   - Restart VS Code after configuration changes
   - Check VS Code output panel for MCP server logs
   - Verify environment variables are loaded

### Debug Mode

Run with debug logging to troubleshoot issues:
```bash
uv run oracle-mcp-server --debug
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a pull request

## Support

- Check the [Issues](https://github.com/yourusername/oracle-mcp-server/issues) page
- Review [sample queries](examples/sample_queries.sql)
- See [configuration examples](examples/github_copilot_config.json)
