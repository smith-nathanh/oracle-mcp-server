#!/usr/bin/env python3
"""
MCP Client that properly communicates with an MCP server using the MCP SDK.

This client follows the MCP protocol by:
1. Connecting to the server via stdio transport
2. Creating a ClientSession for communication
3. Dynamically discovering tools via session.list_tools()
4. Executing tools via session.call_tool()
"""

import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.types import Tool

logger = logging.getLogger(__name__)


def convert_mcp_to_openai_tool(mcp_tool: Tool) -> Dict[str, Any]:
    """Convert an MCP tool definition to OpenAI function calling format."""
    # Extract properties from inputSchema
    properties = mcp_tool.inputSchema.get("properties", {})
    required = mcp_tool.inputSchema.get("required", [])

    # Remove any 'default' keys from properties as OpenAI doesn't use them
    cleaned_properties = {}
    for prop_name, prop_def in properties.items():
        cleaned_properties[prop_name] = {
            k: v for k, v in prop_def.items() if k != "default"
        }

    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": {
                "type": "object",
                "properties": cleaned_properties,
                "required": required,
            },
        },
    }


class MCPClient:
    """Client that communicates with MCP servers using the MCP SDK."""

    def __init__(self, server_script_path: str = None, debug: bool = False):
        """
        Initialize MCP client.

        Args:
            server_script_path: Path to the MCP server script (defaults to oracle-mcp-server)
            debug: Enable debug logging
        """
        self.server_script_path = server_script_path or "oracle-mcp-server"
        self.debug = debug
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._tools_cache: Optional[List[Tool]] = None
        self._openai_tools_cache: Optional[List[Dict[str, Any]]] = None

    async def start_server(self) -> None:
        """Connect to the MCP server using stdio transport."""
        try:
            # Configure server parameters
            env = os.environ.copy()
            if self.debug:
                env["DEBUG"] = "true"

            server_params = StdioServerParameters(
                command="uv", args=["run", self.server_script_path], env=env
            )

            # Connect to server via stdio
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport

            # Create client session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )

            # Initialize the session
            await self.session.initialize()

            # List available tools to verify connection
            response = await self.session.list_tools()
            logger.info(f"Connected to MCP server with {len(response.tools)} tools")
            if self.debug:
                logger.debug(f"Available tools: {[t.name for t in response.tools]}")

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def stop_server(self) -> None:
        """Disconnect from the MCP server."""
        await self.exit_stack.aclose()
        self.session = None
        self._tools_cache = None
        self._openai_tools_cache = None
        logger.info("Disconnected from MCP server")

    async def get_available_tools(self) -> List[Tool]:
        """Get list of available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        # Cache tools to avoid repeated calls
        if self._tools_cache is None:
            response = await self.session.list_tools()
            self._tools_cache = response.tools

        return self._tools_cache

    async def get_tools_as_openai_format(self) -> List[Dict[str, Any]]:
        """Get MCP tools converted to OpenAI function calling format."""
        if self._openai_tools_cache is None:
            mcp_tools = await self.get_available_tools()
            self._openai_tools_cache = [
                convert_mcp_to_openai_tool(tool) for tool in mcp_tools
            ]
        return self._openai_tools_cache

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool through the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool response as a dictionary
        """
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        try:
            # Call tool through the session
            result = await self.session.call_tool(tool_name, arguments)

            # Debug: log the result type and content
            logger.debug(f"Tool result type: {type(result)}")
            logger.debug(f"Tool result: {result}")

            # The result is a CallToolResult with a 'content' attribute containing a list of TextContent
            if hasattr(result, "content") and isinstance(result.content, list):
                # Extract text from the first TextContent object
                if result.content and len(result.content) > 0:
                    text_content = result.content[0]
                    if hasattr(text_content, "text"):
                        # Parse JSON response if possible
                        try:
                            return json.loads(text_content.text)
                        except json.JSONDecodeError:
                            # If not JSON, return as-is in a dict
                            return {"result": text_content.text}
                    else:
                        return {"error": "Unexpected content format"}
                else:
                    return {"error": "No content in response"}
            else:
                # Handle unexpected response format
                return {"result": str(result)}

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_server()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_server()
        return False  # Don't suppress exceptions
