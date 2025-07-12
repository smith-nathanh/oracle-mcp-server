# Oracle MCP Server - Quick Reference

## 🚀 Quick Start

### Docker Setup (Recommended)
```bash
cd docker-example && docker-compose up -d
cp .env.docker ../.env
cd .. && uv run oracle-mcp-server --version
```

### Existing Database Setup
```bash
cp .env.example .env
# Edit .env with your database details
uv run oracle-mcp-server --version
```

## 🔑 Database Credentials (Docker)

```
Username:     testuser
Password:     TestUser123!
Host:         localhost
Port:         1521
Service:      testdb
Connection:   testuser/TestUser123!@localhost:1521/testdb
Admin:        system/Oracle123!@localhost:1521/testdb
```

## 🛠️ Essential Commands

```bash
# Test MCP server
uv run oracle-mcp-server --version

# Check database connection
docker exec oracle-mcp-test sqlplus -S testuser/TestUser123!@localhost:1521/testdb <<< "SELECT 'OK' FROM dual;"

# View database logs
docker logs oracle-mcp-test

# Start/stop database
docker-compose -f docker-example/docker-compose.yml up -d
docker-compose -f docker-example/docker-compose.yml down

# Reset everything
docker-compose -f docker-example/docker-compose.yml down -v
```

## 📊 Sample Data (Docker Setup)

### Tables
- **employees** (4 records): id, first_name, last_name, email, salary, department_id
- **departments** (3 records): id, name, location, budget  
- **employee_details** (view): joined employee + department data

### Quick Queries
```sql
SELECT * FROM employees;
SELECT * FROM departments;
SELECT * FROM employee_details;
SELECT d.name, COUNT(e.id) FROM departments d LEFT JOIN employees e ON d.id = e.department_id GROUP BY d.name;
```

## 🔧 Environment Variables

```bash
# Required
DB_CONNECTION_STRING="testuser/TestUser123!@localhost:1521/testdb"

# Optional
DEBUG="True"
QUERY_LIMIT_SIZE="100"
TABLE_WHITE_LIST=""        # Empty = all tables
COLUMN_WHITE_LIST=""       # Empty = all columns
```

## 🎯 GitHub Copilot Integration

### Example Prompts
- "Show me all tables in the database"
- "Describe the employees table structure"  
- "List employees with their department names"
- "What's the average salary by department?"
- "Export employee data as CSV"

### VS Code Setup
1. Install GitHub Copilot extension
2. Open oracle-mcp-server project folder  
3. Restart VS Code
4. Use Copilot chat to query database

## 🚨 Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Port 1521 in use | `sudo lsof -i :1521` then stop other Oracle instances |
| Out of memory | Close other apps (Oracle needs ~2GB RAM) |
| Permission denied | `sudo usermod -aG docker $USER` then logout/login |
| Connection refused | Wait 2-3 min for DB initialization |
| MCP server fails | Check `.env` file exists and `source .env` |

### Quick Diagnostics
```bash
# Is Docker running?
docker ps | grep oracle-mcp-test

# Is database ready?
docker logs oracle-mcp-test | tail -5

# Can connect?
echo $DB_CONNECTION_STRING

# MCP server working?
uv run oracle-mcp-server --version
```

## 📁 File Structure

```
oracle-mcp-server/
├── docker-example/              # 🐳 Complete Docker setup
│   ├── docker-compose.yml      
│   ├── .env.docker             # Ready-to-use config
│   └── README.md               # Detailed Docker guide
├── .env                        # Your connection config
├── .vscode/mcp.json           # VS Code integration
└── docs/
    ├── SETUP_GUIDE.md         # Complete setup instructions
    └── QUICK_REFERENCE.md     # This file
```

## 📖 More Help

- 🐳 **New users:** Start with [docker-example/README.md](../docker-example/README.md)
- 🔧 **Detailed setup:** See [SETUP_GUIDE.md](SETUP_GUIDE.md)
- 📚 **Project overview:** Check [main README](../README.md)
