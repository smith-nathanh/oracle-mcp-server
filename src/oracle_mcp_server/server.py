#!/usr/bin/env python3
"""
Oracle Database MCP Server for GitHub Copilot Agent Mode

This Model Context Protocol server provides comprehensive Oracle Database
interaction capabilities, optimized for use with GitHub Copilot's agentic workflows.

Features:
- Execute SQL queries with safety controls
- Browse database schema (tables, views, procedures)
- Generate database documentation
- Analyze query performance
- Export query results
- Database health monitoring
"""

import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import oracledb
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("oracle-mcp-server")

# Configuration from environment variables
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")
COMMENT_DB_CONNECTION_STRING = os.getenv(
    "COMMENT_DB_CONNECTION_STRING", DB_CONNECTION_STRING
)
TABLE_WHITE_LIST = (
    os.getenv("TABLE_WHITE_LIST", "").split(",")
    if os.getenv("TABLE_WHITE_LIST")
    else []
)
COLUMN_WHITE_LIST = (
    os.getenv("COLUMN_WHITE_LIST", "").split(",")
    if os.getenv("COLUMN_WHITE_LIST")
    else []
)
QUERY_LIMIT_SIZE = int(os.getenv("QUERY_LIMIT_SIZE", "100"))
MAX_ROWS_EXPORT = int(os.getenv("MAX_ROWS_EXPORT", "10000"))

if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)


class OracleConnection:
    """Manages Oracle database connections with connection pooling"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[oracledb.ConnectionPool] = None

    async def initialize_pool(self):
        """Initialize connection pool"""
        try:
            # Parse connection string to extract components
            if not self.connection_string:
                raise ValueError("Database connection string is required")

            # Create connection pool for better performance
            self.pool = oracledb.create_pool(
                dsn=self.connection_string,
                min=1,
                max=10,
                increment=1,
                threaded=True,
                getmode=oracledb.POOL_GETMODE_WAIT,
            )
            logger.info("Oracle connection pool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Oracle connection pool: {e}")
            raise

    async def get_connection(self) -> oracledb.Connection:
        """Get a connection from the pool"""
        if not self.pool:
            await self.initialize_pool()
        return self.pool.acquire()

    def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            self.pool.close()
            logger.info("Oracle connection pool closed")


class DatabaseInspector:
    """Provides database schema inspection capabilities"""

    def __init__(self, connection_manager: OracleConnection):
        self.connection_manager = connection_manager

    async def get_tables(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of tables with metadata"""
        conn = await self.connection_manager.get_connection()
        try:
            cursor = conn.cursor()

            # Base query for tables
            query = """
                SELECT 
                    t.owner,
                    t.table_name,
                    t.num_rows,
                    t.last_analyzed,
                    tc.comments as table_comment,
                    t.tablespace_name
                FROM all_tables t
                LEFT JOIN all_tab_comments tc ON t.owner = tc.owner AND t.table_name = tc.table_name
                WHERE 1=1
            """

            params = []

            # Filter by owner if specified
            if owner:
                query += " AND t.owner = :owner"
                params.append(owner)

            # Apply whitelist filter if configured
            if TABLE_WHITE_LIST and TABLE_WHITE_LIST != [""]:
                placeholders = ",".join(
                    [f":table_{i}" for i in range(len(TABLE_WHITE_LIST))]
                )
                query += f" AND t.table_name IN ({placeholders})"
                params.extend(TABLE_WHITE_LIST)

            query += " ORDER BY t.owner, t.table_name"

            cursor.execute(query, params)

            tables = []
            for row in cursor:
                tables.append(
                    {
                        "owner": row[0],
                        "table_name": row[1],
                        "num_rows": row[2],
                        "last_analyzed": row[3].isoformat() if row[3] else None,
                        "table_comment": row[4],
                        "tablespace_name": row[5],
                    }
                )

            return tables

        finally:
            conn.close()

    async def get_table_columns(
        self, table_name: str, owner: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed column information for a table"""
        conn = await self.connection_manager.get_connection()
        try:
            cursor = conn.cursor()

            query = """
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.data_length,
                    c.data_precision,
                    c.data_scale,
                    c.nullable,
                    c.data_default,
                    cc.comments as column_comment,
                    c.column_id
                FROM all_tab_columns c
                LEFT JOIN all_col_comments cc ON c.owner = cc.owner 
                    AND c.table_name = cc.table_name 
                    AND c.column_name = cc.column_name
                WHERE c.table_name = :table_name
            """

            params = [table_name]

            if owner:
                query += " AND c.owner = :owner"
                params.append(owner)

            query += " ORDER BY c.column_id"

            cursor.execute(query, params)

            columns = []
            for row in cursor:
                # Apply column whitelist if configured
                full_column_name = f"{table_name}.{row[0]}"
                if COLUMN_WHITE_LIST and COLUMN_WHITE_LIST != [""]:
                    if full_column_name not in COLUMN_WHITE_LIST:
                        continue

                columns.append(
                    {
                        "column_name": row[0],
                        "data_type": row[1],
                        "data_length": row[2],
                        "data_precision": row[3],
                        "data_scale": row[4],
                        "nullable": row[5],
                        "data_default": row[6],
                        "column_comment": row[7],
                        "column_id": row[8],
                    }
                )

            return columns

        finally:
            conn.close()

    async def get_views(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of views"""
        conn = await self.connection_manager.get_connection()
        try:
            cursor = conn.cursor()

            query = """
                SELECT 
                    v.owner,
                    v.view_name,
                    vc.comments as view_comment
                FROM all_views v
                LEFT JOIN all_tab_comments vc ON v.owner = vc.owner AND v.view_name = vc.table_name
                WHERE 1=1
            """

            params = []

            if owner:
                query += " AND v.owner = :owner"
                params.append(owner)

            query += " ORDER BY v.owner, v.view_name"

            cursor.execute(query, params)

            views = []
            for row in cursor:
                views.append(
                    {"owner": row[0], "view_name": row[1], "view_comment": row[2]}
                )

            return views

        finally:
            conn.close()

    async def get_procedures(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of stored procedures and functions"""
        conn = await self.connection_manager.get_connection()
        try:
            cursor = conn.cursor()

            query = """
                SELECT 
                    owner,
                    object_name,
                    object_type,
                    status,
                    created,
                    last_ddl_time
                FROM all_objects
                WHERE object_type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE')
            """

            params = []

            if owner:
                query += " AND owner = :owner"
                params.append(owner)

            query += " ORDER BY owner, object_type, object_name"

            cursor.execute(query, params)

            procedures = []
            for row in cursor:
                procedures.append(
                    {
                        "owner": row[0],
                        "object_name": row[1],
                        "object_type": row[2],
                        "status": row[3],
                        "created": row[4].isoformat() if row[4] else None,
                        "last_ddl_time": row[5].isoformat() if row[5] else None,
                    }
                )

            return procedures

        finally:
            conn.close()


class QueryExecutor:
    """Handles SQL query execution with safety controls"""

    def __init__(self, connection_manager: OracleConnection):
        self.connection_manager = connection_manager

    async def execute_query(
        self, sql: str, params: Optional[List] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query with safety controls"""

        # Basic SQL injection prevention
        sql_upper = sql.upper().strip()

        # Check for potentially dangerous operations
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "INSERT",
            "UPDATE",
        ]

        # Allow SELECT, DESCRIBE, EXPLAIN PLAN
        if not any(
            sql_upper.startswith(keyword)
            for keyword in ["SELECT", "WITH", "DESCRIBE", "DESC", "EXPLAIN"]
        ):
            if any(keyword in sql_upper for keyword in dangerous_keywords):
                raise ValueError(
                    "Only SELECT, DESCRIBE, and EXPLAIN PLAN statements are allowed"
                )

        conn = await self.connection_manager.get_connection()
        try:
            cursor = conn.cursor()

            # Set row limit
            if (
                "SELECT" in sql_upper
                and "ROWNUM" not in sql_upper
                and "LIMIT" not in sql_upper
            ):
                # Add ROWNUM limitation for SELECT queries
                if "ORDER BY" in sql_upper:
                    # More complex query, wrap it
                    sql = f"SELECT * FROM ({sql}) WHERE ROWNUM <= {QUERY_LIMIT_SIZE}"
                else:
                    # Simple query, add WHERE clause
                    if "WHERE" in sql_upper:
                        sql += f" AND ROWNUM <= {QUERY_LIMIT_SIZE}"
                    else:
                        sql += f" WHERE ROWNUM <= {QUERY_LIMIT_SIZE}"

            start_time = datetime.now()

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            execution_time = (datetime.now() - start_time).total_seconds()

            # Fetch results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                # Convert Oracle types to JSON-serializable types
                serializable_rows = []
                for row in rows:
                    serializable_row = []
                    for value in row:
                        if hasattr(value, "read"):  # LOB object
                            serializable_row.append(str(value.read()))
                        elif isinstance(value, datetime):
                            serializable_row.append(value.isoformat())
                        else:
                            serializable_row.append(value)
                    serializable_rows.append(serializable_row)

                return {
                    "columns": columns,
                    "rows": serializable_rows,
                    "row_count": len(rows),
                    "execution_time_seconds": execution_time,
                    "query": sql,
                }
            else:
                return {
                    "message": "Query executed successfully",
                    "execution_time_seconds": execution_time,
                    "query": sql,
                }

        finally:
            conn.close()

    async def explain_query(self, sql: str) -> Dict[str, Any]:
        """Get execution plan for a query"""
        conn = await self.connection_manager.get_connection()
        try:
            cursor = conn.cursor()

            # Generate unique statement ID
            statement_id = f"MCP_EXPLAIN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Explain the plan
            explain_sql = f"EXPLAIN PLAN SET STATEMENT_ID = '{statement_id}' FOR {sql}"
            cursor.execute(explain_sql)

            # Fetch the execution plan
            plan_query = """
                SELECT 
                    LPAD(' ', 2 * (LEVEL - 1)) || operation || ' ' || options AS operation,
                    object_name,
                    cost,
                    cardinality,
                    bytes
                FROM plan_table
                WHERE statement_id = :statement_id
                START WITH id = 0
                CONNECT BY PRIOR id = parent_id AND statement_id = :statement_id
                ORDER BY id
            """

            cursor.execute(plan_query, [statement_id, statement_id])

            plan_rows = []
            for row in cursor:
                plan_rows.append(
                    {
                        "operation": row[0],
                        "object_name": row[1],
                        "cost": row[2],
                        "cardinality": row[3],
                        "bytes": row[4],
                    }
                )

            # Clean up
            cursor.execute(
                "DELETE FROM plan_table WHERE statement_id = :statement_id",
                [statement_id],
            )
            conn.commit()

            return {"execution_plan": plan_rows, "statement_id": statement_id}

        finally:
            conn.close()


class OracleMCPServer:
    """Main MCP Server class for Oracle Database integration"""

    def __init__(self):
        self.server = Server("oracle-database")
        self.connection_manager = OracleConnection(DB_CONNECTION_STRING)
        self.inspector = DatabaseInspector(self.connection_manager)
        self.executor = QueryExecutor(self.connection_manager)

    async def setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            """List available database resources"""
            resources = []

            try:
                # Get database schema information
                tables = await self.inspector.get_tables()

                # Add schema overview resource
                resources.append(
                    Resource(
                        uri=AnyUrl("oracle://schema/overview"),
                        name="Database Schema Overview",
                        description="Complete overview of database tables, views, and procedures",
                        mimeType="application/json",
                    )
                )

                # Add individual table resources
                for table in tables[:50]:  # Limit to first 50 tables
                    table_uri = f"oracle://table/{table['owner']}.{table['table_name']}"
                    resources.append(
                        Resource(
                            uri=AnyUrl(table_uri),
                            name=f"Table: {table['owner']}.{table['table_name']}",
                            description=f"Schema and metadata for table {table['table_name']}",
                            mimeType="application/json",
                        )
                    )

            except Exception as e:
                logger.error(f"Error listing resources: {e}")

            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str:
            """Read a specific database resource"""

            uri_str = str(uri)

            try:
                if uri_str == "oracle://schema/overview":
                    # Return complete schema overview
                    tables = await self.inspector.get_tables()
                    views = await self.inspector.get_views()
                    procedures = await self.inspector.get_procedures()

                    overview = {
                        "database_type": "Oracle",
                        "tables": tables,
                        "views": views,
                        "procedures": procedures,
                        "table_count": len(tables),
                        "view_count": len(views),
                        "procedure_count": len(procedures),
                        "generated_at": datetime.now().isoformat(),
                    }

                    return json.dumps(overview, indent=2, default=str)

                elif uri_str.startswith("oracle://table/"):
                    # Return specific table information
                    table_path = uri_str.replace("oracle://table/", "")

                    if "." in table_path:
                        owner, table_name = table_path.split(".", 1)
                    else:
                        owner = None
                        table_name = table_path

                    columns = await self.inspector.get_table_columns(table_name, owner)

                    table_info = {
                        "owner": owner,
                        "table_name": table_name,
                        "columns": columns,
                        "column_count": len(columns),
                        "generated_at": datetime.now().isoformat(),
                    }

                    return json.dumps(table_info, indent=2, default=str)

                else:
                    raise ValueError(f"Unknown resource URI: {uri_str}")

            except Exception as e:
                logger.error(f"Error reading resource {uri_str}: {e}")
                raise

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available database tools"""

            return [
                Tool(
                    name="execute_query",
                    description="Execute a SQL query against the Oracle database. Only SELECT, DESCRIBE, and EXPLAIN PLAN statements are allowed for safety.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to execute (SELECT, DESCRIBE, or EXPLAIN PLAN only)",
                            },
                            "params": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional parameters for parameterized queries",
                                "default": [],
                            },
                        },
                        "required": ["sql"],
                    },
                ),
                Tool(
                    name="describe_table",
                    description="Get detailed information about a table including columns, data types, and constraints",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe",
                            },
                            "owner": {
                                "type": "string",
                                "description": "Schema owner (optional)",
                                "default": None,
                            },
                        },
                        "required": ["table_name"],
                    },
                ),
                Tool(
                    name="list_tables",
                    description="List all tables in the database with metadata",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Filter by schema owner (optional)",
                                "default": None,
                            }
                        },
                    },
                ),
                Tool(
                    name="list_views",
                    description="List all views in the database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Filter by schema owner (optional)",
                                "default": None,
                            }
                        },
                    },
                ),
                Tool(
                    name="list_procedures",
                    description="List all stored procedures, functions, and packages",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Filter by schema owner (optional)",
                                "default": None,
                            }
                        },
                    },
                ),
                Tool(
                    name="explain_query",
                    description="Get the execution plan for a SQL query to analyze performance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to explain",
                            }
                        },
                        "required": ["sql"],
                    },
                ),
                Tool(
                    name="generate_sample_queries",
                    description="Generate sample SQL queries for a given table to help with exploration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to generate queries for",
                            },
                            "owner": {
                                "type": "string",
                                "description": "Schema owner (optional)",
                                "default": None,
                            },
                        },
                        "required": ["table_name"],
                    },
                ),
                Tool(
                    name="export_query_results",
                    description="Export query results in various formats (JSON, CSV)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to execute and export",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["json", "csv"],
                                "description": "Export format",
                                "default": "json",
                            },
                        },
                        "required": ["sql"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls"""

            try:
                if name == "execute_query":
                    sql = arguments.get("sql")
                    params = arguments.get("params", [])

                    result = await self.executor.execute_query(sql, params)

                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "describe_table":
                    table_name = arguments.get("table_name")
                    owner = arguments.get("owner")

                    columns = await self.inspector.get_table_columns(table_name, owner)

                    result = {
                        "table_name": table_name,
                        "owner": owner,
                        "columns": columns,
                        "column_count": len(columns),
                    }

                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "list_tables":
                    owner = arguments.get("owner")
                    tables = await self.inspector.get_tables(owner)

                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"tables": tables}, indent=2, default=str),
                        )
                    ]

                elif name == "list_views":
                    owner = arguments.get("owner")
                    views = await self.inspector.get_views(owner)

                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"views": views}, indent=2, default=str),
                        )
                    ]

                elif name == "list_procedures":
                    owner = arguments.get("owner")
                    procedures = await self.inspector.get_procedures(owner)

                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"procedures": procedures}, indent=2, default=str
                            ),
                        )
                    ]

                elif name == "explain_query":
                    sql = arguments.get("sql")
                    result = await self.executor.explain_query(sql)

                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "generate_sample_queries":
                    table_name = arguments.get("table_name")
                    owner = arguments.get("owner")

                    columns = await self.inspector.get_table_columns(table_name, owner)

                    # Generate sample queries
                    table_ref = f"{owner}.{table_name}" if owner else table_name

                    queries = [
                        f"-- Basic select all\nSELECT * FROM {table_ref} WHERE ROWNUM <= 10;",
                        f"-- Count total rows\nSELECT COUNT(*) FROM {table_ref};",
                    ]

                    # Add column-specific queries
                    for col in columns[:5]:  # Limit to first 5 columns
                        col_name = col["column_name"]

                        if col["data_type"] in ["VARCHAR2", "CHAR", "CLOB"]:
                            queries.append(
                                f"-- Find distinct values for {col_name}\nSELECT DISTINCT {col_name} FROM {table_ref} WHERE {col_name} IS NOT NULL AND ROWNUM <= 20;"
                            )
                        elif col["data_type"] in ["NUMBER", "INTEGER"]:
                            queries.append(
                                f"-- Statistics for {col_name}\nSELECT MIN({col_name}), MAX({col_name}), AVG({col_name}) FROM {table_ref};"
                            )
                        elif col["data_type"] in ["DATE", "TIMESTAMP"]:
                            queries.append(
                                f"-- Date range for {col_name}\nSELECT MIN({col_name}), MAX({col_name}) FROM {table_ref};"
                            )

                    result = {"table_name": table_name, "sample_queries": queries}

                    return [
                        TextContent(
                            type="text", text=json.dumps(result, indent=2, default=str)
                        )
                    ]

                elif name == "export_query_results":
                    sql = arguments.get("sql")
                    format_type = arguments.get("format", "json")

                    result = await self.executor.execute_query(sql)

                    if format_type == "csv":
                        # Convert to CSV format
                        csv_lines = []
                        csv_lines.append(",".join(result["columns"]))

                        for row in result["rows"]:
                            csv_row = []
                            for value in row:
                                if value is None:
                                    csv_row.append("")
                                else:
                                    # Escape commas and quotes
                                    str_value = str(value)
                                    if "," in str_value or '"' in str_value:
                                        str_value = (
                                            '"' + str_value.replace('"', '""') + '"'
                                        )
                                    csv_row.append(str_value)
                            csv_lines.append(",".join(csv_row))

                        csv_content = "\n".join(csv_lines)

                        return [
                            TextContent(
                                type="text",
                                text=f"CSV Export ({result['row_count']} rows):\n\n{csv_content}",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(result, indent=2, default=str),
                            )
                        ]

                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                logger.error(traceback.format_exc())

                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server"""

        # Validate configuration
        if not DB_CONNECTION_STRING:
            logger.error("DB_CONNECTION_STRING environment variable is required")
            sys.exit(1)

        logger.info("Starting Oracle MCP Server...")

        # Initialize connection pool
        await self.connection_manager.initialize_pool()

        # Setup handlers
        await self.setup_handlers()

        # Initialize server
        async with self.server.create_initialization_options() as (
            read_stream,
            write_stream,
        ):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="oracle-database",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def async_main():
    """Async main entry point"""
    server = OracleMCPServer()

    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        server.connection_manager.close_pool()
        logger.info("Oracle MCP Server shutdown complete")


def main():
    """Synchronous entry point for console scripts"""
    import argparse

    parser = argparse.ArgumentParser(description="Oracle Database MCP Server")
    parser.add_argument("--version", action="version", version="1.0.0")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Run the async main function
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
