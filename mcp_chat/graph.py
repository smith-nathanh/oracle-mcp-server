"""
LangGraph flow for MCP chat - simple conversation with tool usage.
"""

import logging
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from demo.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    """State for the chat conversation."""

    messages: Annotated[List[BaseMessage], add_messages]
    tool_call_count: int
    max_tool_calls: int


class MCPChatGraph:
    """Simple chat graph that lets LLM use MCP tools directly."""

    def __init__(self, llm, mcp_client: MCPClient, console=None):
        self.llm = llm
        self.mcp_client = mcp_client
        self.console = console
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the conversation graph."""
        workflow = StateGraph(ChatState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent", self._should_use_tools, {"continue": "tools", "end": END}
        )

        # Always go back to agent after tools
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get MCP tool definitions in OpenAI format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_tables",
                    "description": "List all tables in the Oracle database with metadata",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Filter by schema owner (optional)",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "describe_table",
                    "description": "Get detailed information about a table including columns, data types, and constraints",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe",
                            },
                            "owner": {
                                "type": "string",
                                "description": "Schema owner (optional)",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_query",
                    "description": "Execute a SQL query against the Oracle database. Only SELECT queries are allowed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to execute (SELECT only)",
                            }
                        },
                        "required": ["sql"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_sample_queries",
                    "description": "Generate sample SQL queries for a given table to help with exploration",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table",
                            },
                            "owner": {
                                "type": "string",
                                "description": "Schema owner (optional)",
                            },
                        },
                        "required": ["table_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "explain_query",
                    "description": "Get the execution plan for a SQL query to analyze performance",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "SQL query to explain",
                            }
                        },
                        "required": ["sql"],
                    },
                },
            },
        ]

    async def _agent_node(self, state: ChatState) -> Dict[str, Any]:
        """Agent decides what to do next."""
        messages = state["messages"]

        # Add system message if this is the first message
        if len(messages) == 1:  # Only user message
            system_msg = SystemMessage(
                content="""You are a helpful Oracle database assistant. You have access to tools that let you:
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
4. Maximum of 5 tool calls per request - prioritize getting the answer efficiently.

When you need more information to answer a question, ask the user for clarification."""
            )
            messages = [system_msg] + messages

        # Show thinking status with tool count
        current_count = state.get("tool_call_count", 0)
        if self.console:
            if current_count > 0:
                self.console.print(f"[dim]🤔 Thinking (after {current_count} tool calls)...[/dim]")
            else:
                self.console.print("[dim]🤔 Analyzing your question...[/dim]")

        # Get response from LLM with tools
        response = await self.llm._agenerate(messages, tools=self._get_tool_definitions())

        ai_message = response.generations[0].message

        # Show what the LLM decided
        if self.console and hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            tool_names = [call["name"] for call in ai_message.tool_calls]
            self.console.print(f"[dim]🔧 Decided to use tools: {', '.join(tool_names)}[/dim]")
        elif self.console and hasattr(ai_message, "content") and ai_message.content:
            self.console.print("[dim]💬 Ready to respond[/dim]")
            # Show a preview of the response
            preview = (
                ai_message.content[:100] + "..."
                if len(ai_message.content) > 100
                else ai_message.content
            )
            self.console.print(f"[dim]Preview: {preview}[/dim]")

        return {"messages": [ai_message]}

    async def _tools_node(self, state: ChatState) -> Dict[str, Any]:
        """Execute tool calls."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check tool call limit
        current_count = state.get("tool_call_count", 0)
        max_calls = state.get("max_tool_calls", 10)

        if current_count >= max_calls:
            logger.warning(f"Maximum tool calls ({max_calls}) reached. Stopping.")
            if self.console:
                self.console.print(
                    f"[yellow]⚠️  Reached tool call limit ({max_calls} calls). Forcing final response.[/yellow]"
                )
            return {
                "messages": [
                    ToolMessage(
                        content="Tool call limit reached. Based on the data gathered so far, please provide your best answer to the user's question.",
                        tool_call_id="limit_reached",
                    )
                ],
                "tool_call_count": current_count,
            }

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": [], "tool_call_count": current_count}

        # Execute each tool call
        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            # Show tool execution
            if self.console:
                self.console.print(f"[dim]⚡ Executing {tool_name}...[/dim]")

            try:
                # Call the MCP tool
                result = await self.mcp_client.call_tool(tool_name, tool_args)

                # Show a preview of the result for debugging
                if self.console:
                    import json

                    if isinstance(result, (dict, list)):
                        result_str = json.dumps(result, indent=2)
                        # Show number of results if it's a list
                        if isinstance(result, list):
                            self.console.print(f"[dim]📊 Got {len(result)} results[/dim]")
                        elif (
                            isinstance(result, dict)
                            and "data" in result
                            and isinstance(result["data"], list)
                        ):
                            self.console.print(f"[dim]📊 Got {len(result['data'])} rows[/dim]")
                        # Show preview
                        preview = result_str[:150] + "..." if len(result_str) > 150 else result_str
                        self.console.print(f"[dim]   Preview: {preview}[/dim]")
                    else:
                        self.console.print(f"[dim]📊 Result: {str(result)[:100]}...[/dim]")

                # Format result as string
                if isinstance(result, dict):
                    content = json.dumps(result, indent=2)
                else:
                    content = str(result)

                tool_messages.append(ToolMessage(content=content, tool_call_id=tool_id))
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                tool_messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_id))

        # Increment tool call count
        new_count = current_count + len(tool_messages)

        return {"messages": tool_messages, "tool_call_count": new_count}

    def _should_use_tools(self, state: ChatState) -> str:
        """Decide whether to use tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # Check if we've hit the tool call limit
        current_count = state.get("tool_call_count", 0)
        max_calls = state.get("max_tool_calls", 10)

        if current_count >= max_calls:
            logger.info(f"Tool call limit ({max_calls}) reached. Ending workflow.")
            return "end"

        # If the last message has tool calls, execute them
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"

        # Otherwise, we're done
        return "end"
