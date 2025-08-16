#!/usr/bin/env python3
"""
Example usage script for the Oracle LangGraph Agent Demo.

This script demonstrates various ways to use the Oracle database research agent
to perform intelligent database exploration and query generation.
"""

import asyncio
import os
from rich.console import Console
from rich.panel import Panel

# Import our demo workflow
from demo.langgraph_demo import OracleResearchWorkflow, display_results

console = Console()


async def run_example(request: str, description: str, connection_string: str):
    """Run a single example request."""
    console.print(Panel(f"[bold]{description}[/bold]\nRequest: {request}", 
                       title="Example Demo"))
    
    workflow = OracleResearchWorkflow(connection_string, debug=True)
    results = await workflow.research(request)
    
    display_results(results)
    
    console.print("\n" + "="*80 + "\n")
    return results


async def main():
    """Run example demonstrations."""
    
    # Get connection string
    connection_string = os.getenv("DB_CONNECTION_STRING")
    if not connection_string:
        console.print("[red]Error:[/red] Set DB_CONNECTION_STRING environment variable")
        console.print("Example: export DB_CONNECTION_STRING='testuser/TestUser123!@localhost:1521/testdb'")
        return
    
    console.print(Panel("[bold blue]Oracle LangGraph Agent Demo Examples[/bold blue]\n"
                       "This demo showcases intelligent database research using LangGraph agents", 
                       title="Welcome"))
    
    # Example 1: Basic database exploration
    await run_example(
        "Show me all the tables in the database",
        "Basic Database Exploration",
        connection_string
    )
    
    # Example 2: Find specific data
    await run_example(
        "Find all employees and show me sample data",
        "Data Discovery and Sampling", 
        connection_string
    )
    
    # Example 3: Business analysis
    await run_example(
        "Analyze our sales data and show me trends",
        "Business Data Analysis",
        connection_string
    )
    
    # Example 4: Performance analysis
    await run_example(
        "Show me the execution plan for queries on the largest table",
        "Query Performance Analysis",
        connection_string
    )
    
    console.print(Panel("[green]Demo Complete![/green]\n"
                       "The Oracle LangGraph agent successfully demonstrated:\n"
                       "• Intelligent database schema discovery\n"
                       "• Contextual query generation\n" 
                       "• Multi-turn research workflows\n"
                       "• Performance analysis and optimization\n"
                       "• Rich result formatting and insights", 
                       title="Summary"))


if __name__ == "__main__":
    asyncio.run(main())