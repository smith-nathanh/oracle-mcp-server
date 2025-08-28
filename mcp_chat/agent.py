"""
Database agent that processes queries with MCP tools using OpenAI client pattern.
Based on the OpenRouter MCP docs pattern but adapted for our Oracle MCP server.
"""

import json
import logging
from typing import Any, Dict, List

from .llm import OpenRouterLLM
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class DatabaseAgent:
    """Database agent that handles multistep tool usage for Oracle database queries."""

    def __init__(self, llm: OpenRouterLLM, mcp_client: MCPClient, console=None):
        self.llm = llm
        self.mcp_client = mcp_client
        self.console = console
        self.messages: List[Dict[str, Any]] = []

    def _add_system_message(self):
        """Add system message if this is the first conversation."""
        if not self.messages:
            system_message = {
                "role": "system",
                "content": """You are a helpful Oracle database assistant. You have access to tools that let you:
- List tables in the database
- Describe table structures  
- Execute SELECT queries
- Generate sample queries
- Analyze query performance

Use these tools to help answer user questions about their database. Always start by understanding the schema before writing queries.

IMPORTANT RULES:
1. After executing a query that returns the data needed to answer the user's question, you MUST provide a final answer immediately.
2. Do NOT continue using tools after you have the answer data.
3. When you execute a query and get results, analyze them and provide your conclusion.
4. Maximum of 8 tool calls per request - prioritize getting the answer efficiently.

When you need more information to answer a question, ask the user for clarification.""",
            }
            self.messages.append(system_message)

    async def process_query(self, query: str, max_iterations: int = 8) -> str:
        """
        Process a user query with multistep tool usage.

        Args:
            query: The user's question
            max_iterations: Maximum number of LLM calls to prevent infinite loops

        Returns:
            Final response from the LLM
        """
        # Add system message if needed
        self._add_system_message()

        # Add user message
        self.messages.append({"role": "user", "content": query})

        # Get available tools
        available_tools = await self.mcp_client.get_tools_as_openai_format()

        iteration_count = 0

        while iteration_count < max_iterations:
            iteration_count += 1

            if self.console:
                self.console.print(
                    f"[green]Analyzing (iteration {iteration_count})...[/green]"
                )

            # Get LLM response with vLLM error handling
            try:
                response = await self.llm.create_completion(
                    messages=self.messages, tools=available_tools
                )
            except Exception as e:
                # Check for vLLM single tool call limitation error
                if "model only supports one tool call" in str(e).lower() or "single tool call" in str(e).lower():
                    if self.console:
                        self.console.print("[yellow]vLLM limitation detected - retrying with sequential tool calls[/yellow]")
                    
                    # Retry with sequential tool calling approach
                    response = await self._handle_vllm_sequential_retry(available_tools)
                else:
                    # Re-raise other errors
                    raise

            choice = response["choices"][0]
            message = choice["message"]

            # Add assistant message to conversation
            self.messages.append(message)

            # Check if LLM wants to use tools
            if "tool_calls" in message and message["tool_calls"]:
                tool_calls = message["tool_calls"]

                if self.console:
                    tool_names = [tc["function"]["name"] for tc in tool_calls]
                    self.console.print(
                        f"[green]Using tools: {', '.join(tool_names)}[/green]"
                    )

                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    tool_id = tool_call["id"]

                    if self.console:
                        self.console.print(f"[green]Executing {tool_name}...[/green]")

                    try:
                        # Call the MCP tool
                        result = await self.mcp_client.call_tool(tool_name, tool_args)

                        # Show preview of result
                        if self.console:
                            if isinstance(result, dict):
                                # Show useful preview
                                preview_text = (
                                    json.dumps(result, indent=2)[:200] + "..."
                                    if len(str(result)) > 200
                                    else json.dumps(result, indent=2)
                                )
                                self.console.print(
                                    f"[dim]   Preview: {preview_text}[/dim]"
                                )

                        # Convert result to string for tool message
                        result_content = (
                            json.dumps(result, indent=2)
                            if isinstance(result, dict)
                            else str(result)
                        )

                        # Add tool result to conversation
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": result_content,
                        }
                        self.messages.append(tool_message)

                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        # Add error message to conversation
                        error_message = {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": f"Error: {str(e)}",
                        }
                        self.messages.append(error_message)

                # Continue the loop to get LLM response to tool results
                continue

            else:
                # No tool calls - LLM provided final response
                if self.console:
                    self.console.print("[green]Ready to respond[/green]")
                    if message.get("content"):
                        preview = (
                            message["content"][:100] + "..."
                            if len(message["content"]) > 100
                            else message["content"]
                        )
                        self.console.print(f"[dim]Preview: {preview}[/dim]")
                    self.console.print("[green]Processing complete[/green]")

                # Return the final response content
                return message.get("content", "")

        # If we hit max iterations, return what we have
        logger.warning(f"Reached maximum iterations ({max_iterations})")
        return "I've reached the maximum number of processing steps. Based on what I've discovered so far, let me provide you with the available information."

    async def _handle_vllm_sequential_retry(self, available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle vLLM sequential retry by making individual tool calls."""
        # First, get the LLM's intended response without tools to understand what it wants to do
        response = await self.llm.create_completion(
            messages=self.messages
        )
        
        choice = response["choices"][0]
        message = choice["message"]
        
        # If the LLM provides a text response, we need to infer what tools it would want
        # For now, let's try common tools one at a time based on the user's query
        if message.get("content"):
            # Try to determine which tool to use based on context
            user_query = self.messages[-1]["content"].lower() if self.messages else ""
            
            # Simple heuristics for tool selection
            if "table" in user_query or "schema" in user_query:
                tool_name = "list_tables"
            elif "describe" in user_query or "structure" in user_query:
                tool_name = "describe_table"
            elif "select" in user_query or "query" in user_query:
                tool_name = "execute_query"
            else:
                # Default to list_tables as a starting point
                tool_name = "list_tables"
            
            # Find the tool in available tools
            selected_tool = next((t for t in available_tools if t["function"]["name"] == tool_name), None)
            
            if selected_tool and self.console:
                self.console.print(f"[cyan]vLLM workaround: Trying {tool_name}[/cyan]")
            
            if selected_tool:
                # Make a new call with just this one tool
                try:
                    single_tool_response = await self.llm.create_completion(
                        messages=self.messages,
                        tools=[selected_tool],
                        tool_choice={"type": "function", "function": {"name": tool_name}}
                    )
                    return single_tool_response
                except Exception as e:
                    if self.console:
                        self.console.print(f"[red]Single tool call also failed: {e}[/red]")
                    # Fall back to no-tool response
                    return response
        
        return response

    def clear_conversation(self):
        """Clear the conversation history."""
        self.messages = []
