#!/usr/bin/env python3
"""
Simple CLI chat interface for Oracle MCP server using LangGraph.

This demonstrates how any LLM can use the MCP tools to answer
questions about the database through natural conversation.
"""

import asyncio
import os
import sys
from typing import Optional
import typer

# Try to load .env file if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from langchain_core.messages import HumanMessage
import logging

from demo.mcp_client import MCPClient
from .llm import OpenRouterLLM
from .graph import MCPChatGraph, ChatState

# Setup logging - suppress by default
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

console = Console()
app = typer.Typer()


async def run_chat_loop(
    llm: OpenRouterLLM,
    mcp_client: MCPClient,
    initial_message: Optional[str] = None,
    debug: bool = False,
    timeout: float = 60.0,
):
    """Run the interactive chat loop."""
    # Create the graph with status callback
    graph = MCPChatGraph(llm, mcp_client, console)
    workflow = graph.graph

    # Initialize state with loop protection
    state = ChatState(messages=[], tool_call_count=0, max_tool_calls=10)

    console.print(
        Panel(
            "[bold blue]Oracle Database Assistant[/bold blue]\n"
            "I can help you explore and query your Oracle database.\n"
            "Type [yellow]'exit'[/yellow] to quit, [yellow]'clear'[/yellow] to start over.",
            title="Welcome",
        )
    )

    # Process initial message if provided
    if initial_message:
        console.print(f"\n[green]You:[/green] {initial_message}")
        state["messages"].append(HumanMessage(content=initial_message))

        # Get response with timeout protection
        try:
            console.print("[dim]Processing your request...[/dim]")
            result = await asyncio.wait_for(workflow.ainvoke(state), timeout=timeout)
            state = result
            console.print("[dim]✓ Processing complete[/dim]")
        except asyncio.TimeoutError:
            console.print(f"\n[red]⏱️  Request timed out after {int(timeout)} seconds.[/red]")
            console.print(
                "[yellow]The query was complex and needed more time. Here's what was discovered so far:[/yellow]"
            )
            # Show any AI messages with content that were generated
            from langchain_core.messages import AIMessage

            ai_messages = [
                msg
                for msg in state["messages"]
                if isinstance(msg, AIMessage) and hasattr(msg, "content") and msg.content
            ]
            if ai_messages:
                for msg in ai_messages:
                    console.print(Markdown(msg.content))
            return

        # Display response - find all AI messages with content (excluding tool-only messages)
        from langchain_core.messages import AIMessage

        ai_messages_with_content = [
            msg
            for msg in state["messages"]
            if isinstance(msg, AIMessage) and hasattr(msg, "content") and msg.content
        ]

        if ai_messages_with_content:
            # Show all AI responses, not just the last one
            for ai_msg in ai_messages_with_content:
                console.print("\n[blue]Assistant:[/blue]")
                console.print(Markdown(ai_msg.content))
        else:
            # Check if we're still processing (last message is AI with tool calls)
            last_msg = state["messages"][-1] if state["messages"] else None
            if (
                last_msg
                and isinstance(last_msg, AIMessage)
                and hasattr(last_msg, "tool_calls")
                and last_msg.tool_calls
            ):
                console.print("\n[dim]Still processing with tools...[/dim]")
            else:
                console.print(
                    "\n[yellow]The assistant is still thinking. It may need more time to complete the task.[/yellow]"
                )

        # If we had an initial message, exit here (don't start interactive loop)
        console.print()  # Add blank line before connection closes
        return

    # Main chat loop (only runs if no initial message)
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[green]You[/green]")

            if user_input.lower() == "exit":
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif user_input.lower() == "clear":
                state = ChatState(messages=[], tool_call_count=0, max_tool_calls=10)
                console.clear()
                console.print("[yellow]Conversation cleared.[/yellow]")
                continue

            # Add user message
            state["messages"].append(HumanMessage(content=user_input))

            # Get response with timeout protection
            try:
                result = await asyncio.wait_for(workflow.ainvoke(state), timeout=timeout)
                state = result
            except asyncio.TimeoutError:
                console.print(
                    f"[red]Request timed out after {int(timeout)} seconds. Please try a simpler question.[/red]"
                )
                continue

            # Display response - find all AI messages with content (excluding tool-only messages)
            from langchain_core.messages import AIMessage

            ai_messages_with_content = [
                msg
                for msg in state["messages"]
                if isinstance(msg, AIMessage) and hasattr(msg, "content") and msg.content
            ]

            if ai_messages_with_content:
                # Show the most recent AI response with content
                last_ai_msg = ai_messages_with_content[-1]
                console.print("\n[blue]Assistant:[/blue]")
                console.print(Markdown(last_ai_msg.content))
            else:
                # Check if we're still processing (last message is AI with tool calls)
                last_msg = state["messages"][-1] if state["messages"] else None
                if (
                    last_msg
                    and isinstance(last_msg, AIMessage)
                    and hasattr(last_msg, "tool_calls")
                    and last_msg.tool_calls
                ):
                    console.print("\n[dim]Still processing with tools...[/dim]")
                else:
                    console.print(
                        "\n[yellow]The assistant is still thinking. Try asking a follow-up question.[/yellow]"
                    )

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            continue
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            logger.error(f"Chat error: {e}", exc_info=True)


@app.command()
def main(
    model: str = typer.Option(
        None, "--model", "-m", help="OpenRouter model to use (e.g., 'anthropic/claude-3-haiku')"
    ),
    api_key: str = typer.Option(
        None, "--api-key", "-k", help="OpenRouter API key (or set OPENROUTER_API_KEY env var)"
    ),
    connection: str = typer.Option(
        None,
        "--connection",
        "-c",
        help="Oracle connection string (or set DB_CONNECTION_STRING env var)",
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    message: str = typer.Argument(None, help="Initial message to send (optional)"),
    timeout: float = typer.Option(
        60.0, "--timeout", "-t", help="Timeout in seconds for each request (default: 60)"
    ),
):
    """
    Chat with your Oracle database using natural language.

    This demo shows how an LLM can use MCP tools to explore and query
    your database through conversation.

    Examples:

    \b
    # Interactive chat
    python -m mcp_chat.chat

    \b
    # Start with a specific question
    python -m mcp_chat.chat "Show me all customer tables"

    \b
    # Use a different model
    python -m mcp_chat.chat --model anthropic/claude-3-opus
    """

    # Setup logging
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        # Suppress all logging except errors
        logging.getLogger().setLevel(logging.ERROR)

    # Get connection string
    connection_string = connection or os.getenv("DB_CONNECTION_STRING")
    if not connection_string:
        console.print(
            "[red]Error:[/red] Database connection required. Set DB_CONNECTION_STRING env var."
        )
        raise typer.Exit(1)

    # Create LLM
    try:
        llm = OpenRouterLLM(api_key=api_key, model=model)
        console.print(f"[dim]Using model: {llm.model}[/dim]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Create MCP client
    mcp_client = MCPClient(connection_string, debug)

    async def run():
        async with mcp_client:
            await run_chat_loop(llm, mcp_client, message, debug, timeout)

    # Run the async main
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if debug:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
