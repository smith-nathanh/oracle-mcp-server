# Oracle MCP Server - Docker Example

This directory contains everything you need to run a complete Oracle database test environment for the Oracle MCP Server.

## What's Included

- **Oracle Database XE 21c** running in Docker
- **Sample database** with realistic test data
- **Pre-configured user** with appropriate permissions
- **Sample tables** (employees, departments) 
- **Ready-to-use connection settings**

## Quick Start

### 1. Install Docker

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER  # Requires logout/login
```

**macOS:**
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or using Homebrew:
brew install --cask docker
```

### 2. Start the Database

```bash
# From the docker-example directory
cd docker-example

# Start Oracle Database (takes 2-3 minutes on first run)
docker-compose up -d

# Monitor startup progress
docker logs -f oracle-mcp-test

# Wait for: "DATABASE IS READY TO USE!"
```

### 3. Configure the MCP Server

```bash
# Copy the Docker environment file to the main project
cp .env.docker ../.env

# Test the connection
cd ..
uv run oracle-mcp-server --version
```

## Database Credentials

| Parameter | Value |
|-----------|-------|
| **Username** | `testuser` |
| **Password** | `TestUser123!` |
| **Host** | `localhost` |
| **Port** | `1521` |
| **Service** | `testdb` |
| **Connection String** | `testuser/TestUser123!@localhost:1521/testdb` |

**Admin Access:**
- **Username:** `system`
- **Password:** `Oracle123!`

## Sample Data

The database includes realistic test data:

### Employees Table
```sql
SELECT * FROM employees;
```
| ID | First Name | Last Name | Email | Salary | Department |
|----|------------|-----------|-------|--------|------------|
| 1 | John | Doe | john.doe@company.com | $75,000 | Engineering |
| 2 | Jane | Smith | jane.smith@company.com | $85,000 | Engineering |
| 3 | Bob | Johnson | bob.johnson@company.com | $65,000 | Marketing |
| 4 | Alice | Brown | alice.brown@company.com | $70,000 | Sales |

### Departments Table
```sql
SELECT * FROM departments;
```
| ID | Name | Location | Budget |
|----|------|----------|--------|
| 1 | Engineering | San Francisco | $5,000,000 |
| 2 | Marketing | New York | $2,000,000 |
| 3 | Sales | Chicago | $3,000,000 |

### Employee Details View
```sql
SELECT * FROM employee_details;
```
A joined view showing employee and department information together.

## Testing Queries

Try these queries through GitHub Copilot or direct database access:

```sql
-- List all employees with their departments
SELECT 
    e.first_name || ' ' || e.last_name AS full_name,
    e.email,
    e.salary,
    d.name AS department,
    d.location
FROM employees e
JOIN departments d ON e.department_id = d.id;

-- Average salary by department
SELECT 
    d.name AS department,
    ROUND(AVG(e.salary), 2) AS avg_salary,
    COUNT(e.id) AS employee_count
FROM departments d
LEFT JOIN employees e ON d.id = e.department_id
GROUP BY d.name;

-- Department budget utilization
SELECT 
    d.name AS department,
    d.budget,
    COALESCE(SUM(e.salary), 0) AS total_salaries,
    d.budget - COALESCE(SUM(e.salary), 0) AS remaining_budget
FROM departments d
LEFT JOIN employees e ON d.id = e.department_id
GROUP BY d.name, d.budget;
```

## VS Code Integration

1. **Copy environment:** `cp docker-example/.env.docker .env`
2. **Open project** in VS Code
3. **Install GitHub Copilot** extension
4. **Restart VS Code** to load MCP configuration
5. **Test with Copilot:** "Show me all tables in the database"

## Management Commands

```bash
# Start database
docker-compose up -d

# Stop database (preserves data)
docker-compose stop

# View logs
docker logs oracle-mcp-test

# Connect to database
docker exec -it oracle-mcp-test sqlplus testuser/TestUser123!@localhost:1521/testdb

# Remove everything (including data)
docker-compose down -v

# Check container status
docker ps
```

## File Structure

```
docker-example/
├── docker-compose.yml          # Database container configuration
├── .env.docker                 # MCP server connection settings
├── setup_testuser.sql          # Database initialization script
├── init-scripts/
│   └── 01-sample-data.sql     # Sample data creation
└── README.md                   # This file
```

## Troubleshooting

### Database Won't Start
```bash
# Check Docker is running
sudo systemctl status docker

# Check logs for errors
docker logs oracle-mcp-test

# Ensure port 1521 is available
netstat -an | grep 1521
```

### Connection Issues
```bash
# Test database connectivity
docker exec oracle-mcp-test sqlplus -S testuser/TestUser123!@localhost:1521/testdb <<< "SELECT 'OK' FROM dual;"

# Check environment variables
source .env.docker && echo $DB_CONNECTION_STRING
```

### Out of Memory
- Oracle requires ~2GB RAM minimum
- Close other applications if needed
- Check with: `docker stats oracle-mcp-test`

### Reset Everything
```bash
# Complete reset
docker-compose down -v
docker-compose up -d
```

## System Requirements

- **RAM:** 8GB+ recommended (Oracle needs ~2GB)
- **Disk:** 4GB+ free space
- **Network:** Internet connection for initial image download
- **OS:** Linux, macOS, or Windows with WSL2

## Security Note

⚠️ **This setup is for development/testing only:**
- Uses default passwords
- Database accessible on localhost:1521
- Overly permissive user privileges
- No SSL/TLS encryption

For production use, implement proper security measures.

## Next Steps

Once your Docker setup is working:

1. **Explore the sample data** using GitHub Copilot
2. **Try the example queries** above
3. **Add your own test data** 
4. **Experiment with Oracle SQL features**
5. **Integrate with your own projects**

For more detailed information, see the main project documentation.
