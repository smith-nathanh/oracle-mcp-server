# Oracle MCP Server - Complete Setup Guide

This guide provides step-by-step instructions for setting up the Oracle MCP Server with any Oracle database (cloud, on-premises, or Docker).

## Setup Options

Choose the setup method that works best for you:

### 🐳 Docker Setup (Recommended for Testing)
**Perfect for:** First-time users, testing, development

Use our ready-made Docker setup with Oracle XE and sample data:
```bash
cd docker-example
# Follow the README.md in that directory
```

📖 **[Complete Docker Setup Guide →](../docker-example/README.md)**

### 🏢 Existing Oracle Database
**Perfect for:** Production use, existing Oracle infrastructure

If you already have access to an Oracle database, skip to [Configuration](#configuration) below.

### ☁️ Oracle Cloud Setup
**Perfect for:** Cloud deployments, production workloads

1. Create an Oracle Autonomous Database in Oracle Cloud
2. Download the wallet files
3. Configure TNS_ADMIN environment variable
4. Use the cloud connection string format

## Configuration

### Environment Setup

1. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Update connection string** in `.env`:
   ```bash
   # For Docker setup:
   DB_CONNECTION_STRING="testuser/TestUser123!@localhost:1521/testdb"
   
   # For existing Oracle database:
   DB_CONNECTION_STRING="username/password@hostname:port/service_name"
   
   # For Oracle Cloud:
   DB_CONNECTION_STRING="username/password@hostname:port/service_name"
   ```

3. **Optional settings:**
   ```bash
   DEBUG="True"                    # Enable detailed logging
   QUERY_LIMIT_SIZE="100"          # Limit query results
   TABLE_WHITE_LIST=""             # Restrict table access (comma-separated)
   COLUMN_WHITE_LIST=""            # Restrict column access
   ```

### Test the Setup

```bash
# Test MCP server
uv run oracle-mcp-server --version

# Test database connection
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}}}' | uv run oracle-mcp-server
# Look for: "Oracle connection pool initialized successfully"
```

## VS Code Integration

### Install Required Extensions
1. Open VS Code
2. Install extensions:
   - **GitHub Copilot** (required for MCP integration)
   - **Python** (recommended for development)

### Configure MCP
1. Open the `oracle-mcp-server` project folder in VS Code
2. The project includes a pre-configured `.vscode/mcp.json` file
3. Restart VS Code to load the MCP configuration

### Test Integration
1. Open a new chat with GitHub Copilot
2. Try these commands:
   - "Show me all tables in the database"
   - "Describe the employees table structure"
   - "List all employees with their departments"

## Connection String Formats

The MCP server supports multiple connection string formats:

### Simple Format (Recommended)
```bash
# Traditional Oracle format
DB_CONNECTION_STRING="username/password@hostname:port/service_name"

# Examples:
DB_CONNECTION_STRING="testuser/TestUser123!@localhost:1521/testdb"
DB_CONNECTION_STRING="hr/password@myserver:1521/PROD"
```

### URL Format (Alternative)
```bash
# SQLAlchemy-style URL format
DB_CONNECTION_STRING="oracle+oracledb://username:password@hostname:port/?service_name=service_name"

# Examples:
DB_CONNECTION_STRING="oracle+oracledb://hr:password@localhost:1521/?service_name=XEPDB1"
DB_CONNECTION_STRING="oracle+oracledb://app_user:password@db.company.com:1521/?service_name=PROD"
```

### Oracle Cloud Format
```bash
# For Autonomous Database with wallet
DB_CONNECTION_STRING="username/password@service_name"
# Requires TNS_ADMIN environment variable pointing to wallet directory
```

## Environment Variables Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DB_CONNECTION_STRING` | Oracle connection string | *Required* | `testuser/TestUser123!@localhost:1521/testdb` |
| `COMMENT_DB_CONNECTION_STRING` | Separate connection for metadata | Same as DB_CONNECTION_STRING | `readonly_user/pass@localhost:1521/testdb` |
| `TABLE_WHITE_LIST` | Allowed tables (comma-separated) | All tables | `EMPLOYEES,DEPARTMENTS` |
| `COLUMN_WHITE_LIST` | Allowed columns (TABLE.COLUMN format) | All columns | `EMPLOYEES.ID,EMPLOYEES.NAME` |
| `QUERY_LIMIT_SIZE` | Maximum rows per query | `100` | `500` |
| `MAX_ROWS_EXPORT` | Maximum rows for exports | `10000` | `50000` |
| `DEBUG` | Enable debug logging | `False` | `True` |

## Troubleshooting

### Common Connection Issues

**"DB_CONNECTION_STRING environment variable is required"**
```bash
# Check if .env file exists and is loaded
ls -la .env
source .env && echo $DB_CONNECTION_STRING
```

**"Oracle connection pool initialization failed"**
```bash
# Test connection string format
echo $DB_CONNECTION_STRING

# Common issues:
# - Incorrect hostname/port
# - Wrong service name
# - Invalid credentials
# - Database not running
```

**"TNS:could not resolve the connect identifier"**
```bash
# For Oracle Cloud with wallet:
echo $TNS_ADMIN  # Should point to wallet directory

# For service names, verify the service exists:
# Connect as DBA: SELECT name FROM v$services;
```

### MCP Server Issues

**"Server exited before responding to initialize request"**
```bash
# Check MCP server logs for specific error
uv run oracle-mcp-server --debug

# Common causes:
# - Database connection failure
# - Missing dependencies
# - Environment variable issues
```

**VS Code integration not working:**
1. Verify `.vscode/mcp.json` exists in workspace root
2. Restart VS Code completely
3. Check GitHub Copilot extension is enabled
4. Test environment variables in VS Code terminal

### Performance Issues

**Slow query responses:**
```bash
# Increase query limits
QUERY_LIMIT_SIZE="50"  # Reduce from default 100

# Check database performance
# Connect to database and run:
# SELECT sql_text, executions, elapsed_time FROM v$sql ORDER BY elapsed_time DESC;
```

**Memory issues:**
```bash
# Monitor MCP server memory usage
ps aux | grep oracle-mcp-server

# For Docker setups, see docker-example/README.md for container-specific troubleshooting
```

## Security Considerations

### Production Deployment

- **Use strong passwords** and change default credentials
- **Limit table/column access** using WHITE_LIST environment variables
- **Use read-only database users** when possible
- **Enable SSL/TLS** for database connections
- **Network security** - restrict database access to necessary hosts only
- **Monitor access** - enable database auditing for production use

### Environment Variables Security

```bash
# Use secure .env file permissions
chmod 600 .env

# For production, consider using:
# - Docker secrets
# - Kubernetes secrets  
# - Cloud provider secret management
# - Environment variable injection at runtime
```

## Next Steps

Once your setup is working:

1. **Test with sample queries** using GitHub Copilot
2. **Explore your database schema** through the MCP server
3. **Configure table/column filtering** for security
4. **Set up monitoring** for production deployments
5. **Customize query limits** based on your needs

## Related Documentation

- 🐳 **[Docker Example Setup](../docker-example/README.md)** - Complete Docker environment
- 📝 **[Quick Reference](QUICK_REFERENCE.md)** - Commands and troubleshooting
- 🔧 **[Main README](../README.md)** - Project overview and features
