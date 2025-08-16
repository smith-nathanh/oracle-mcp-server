#!/usr/bin/env python3
"""
Simplified MCP Client for Oracle Database integration with LangGraph agents.

This module provides a simplified client that directly imports and uses 
the Oracle MCP server components without subprocess communication.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

# Import the Oracle MCP server components directly
from oracle_mcp_server.server import OracleMCPServer

logger = logging.getLogger(__name__)


class MCPClient:
    """Simplified client that directly uses Oracle MCP server components."""

    def __init__(self, connection_string: str, debug: bool = False):
        """
        Initialize MCP client.
        
        Args:
            connection_string: Oracle database connection string
            debug: Enable debug logging
        """
        self.connection_string = connection_string
        self.debug = debug
        self.server: Optional[OracleMCPServer] = None
        
    async def start_server(self) -> None:
        """Initialize the MCP server components."""
        try:
            # Set environment variables for the server
            os.environ["DB_CONNECTION_STRING"] = self.connection_string
            os.environ["DEBUG"] = str(self.debug)
            os.environ["QUERY_LIMIT_SIZE"] = "100"
            os.environ["MAX_ROWS_EXPORT"] = "10000"
            
            # Create and initialize the server
            self.server = OracleMCPServer()
            await self.server.connection_manager.initialize_pool()
            
            logger.info("MCP server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def stop_server(self) -> None:
        """Stop the MCP server."""
        if self.server:
            self.server.connection_manager.close_pool()
            self.server = None
            logger.info("MCP server stopped")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool directly on the server components.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        if not self.server:
            raise RuntimeError("MCP server is not running")
            
        try:
            # Call the tool directly through the server's tool handler
            if tool_name == "execute_query":
                sql = arguments.get("sql")
                params = arguments.get("params", [])
                result = await self.server.executor.execute_query(sql, params)
                return result
                
            elif tool_name == "describe_table":
                table_name = arguments.get("table_name")
                owner = arguments.get("owner")
                columns = await self.server.inspector.get_table_columns(table_name, owner)
                return {
                    "table_name": table_name,
                    "owner": owner,
                    "columns": columns,
                    "column_count": len(columns),
                }
                
            elif tool_name == "list_tables":
                owner = arguments.get("owner")
                tables = await self.server.inspector.get_tables(owner)
                return {"tables": tables}
                
            elif tool_name == "list_views":
                owner = arguments.get("owner")
                views = await self.server.inspector.get_views(owner)
                return {"views": views}
                
            elif tool_name == "list_procedures":
                owner = arguments.get("owner")
                procedures = await self.server.inspector.get_procedures(owner)
                return {"procedures": procedures}
                
            elif tool_name == "explain_query":
                sql = arguments.get("sql")
                result = await self.server.executor.explain_query(sql)
                return result
                
            elif tool_name == "generate_sample_queries":
                table_name = arguments.get("table_name")
                owner = arguments.get("owner")
                columns = await self.server.inspector.get_table_columns(table_name, owner)
                
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
                
                return {"table_name": table_name, "sample_queries": queries}
                
            elif tool_name == "export_query_results":
                sql = arguments.get("sql")
                format_type = arguments.get("format", "json")
                result = await self.server.executor.execute_query(sql)
                
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
                                str_value = str(value)
                                if "," in str_value or '"' in str_value:
                                    str_value = '"' + str_value.replace('"', '""') + '"'
                                csv_row.append(str_value)
                        csv_lines.append(",".join(csv_row))
                    
                    csv_content = "\n".join(csv_lines)
                    return {"csv_content": csv_content, "row_count": result["row_count"]}
                else:
                    return result
            
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    async def execute_query(self, sql: str, params: Optional[List] = None) -> Dict[str, Any]:
        """Execute a SQL query."""
        return await self.call_tool("execute_query", {"sql": sql, "params": params or []})

    async def describe_table(self, table_name: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Describe a table structure."""
        args = {"table_name": table_name}
        if owner:
            args["owner"] = owner
        return await self.call_tool("describe_table", args)

    async def list_tables(self, owner: Optional[str] = None) -> Dict[str, Any]:
        """List all tables."""
        args = {}
        if owner:
            args["owner"] = owner
        return await self.call_tool("list_tables", args)

    async def list_views(self, owner: Optional[str] = None) -> Dict[str, Any]:
        """List all views."""
        args = {}
        if owner:
            args["owner"] = owner
        return await self.call_tool("list_views", args)

    async def list_procedures(self, owner: Optional[str] = None) -> Dict[str, Any]:
        """List all procedures."""
        args = {}
        if owner:
            args["owner"] = owner
        return await self.call_tool("list_procedures", args)

    async def explain_query(self, sql: str) -> Dict[str, Any]:
        """Get execution plan for a query."""
        return await self.call_tool("explain_query", {"sql": sql})

    async def generate_sample_queries(self, table_name: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Generate sample queries for a table."""
        args = {"table_name": table_name}
        if owner:
            args["owner"] = owner
        return await self.call_tool("generate_sample_queries", args)

    async def export_query_results(self, sql: str, format_type: str = "json") -> Dict[str, Any]:
        """Export query results in specified format."""
        return await self.call_tool("export_query_results", {"sql": sql, "format": format_type})

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_server()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_server()


# Add missing import
import os