#!/usr/bin/env python3
"""
LangGraph Oracle Database Research Agent Demo.

This module provides a complete demonstration of using LangGraph agents
to perform intelligent database research and query generation, similar
to how GitHub Copilot interacts with the Oracle MCP server.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any

try:
    from langgraph.graph import StateGraph, END
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import typer
except ImportError as e:
    print(f"Demo dependencies not installed. Run: uv sync --group demo")
    print(f"Missing: {e}")
    sys.exit(1)

from demo.agent_state import AgentState, AgentRole, create_initial_state, format_schema_summary
from demo.agents import PlannerAgent, ExplorerAgent, QueryGeneratorAgent, AnalystAgent, CoordinatorAgent
from demo.mcp_client import MCPClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rich console for beautiful output
console = Console()

app = typer.Typer(help="Oracle Database Research Agent Demo using LangGraph")


class OracleResearchWorkflow:
    """
    LangGraph workflow for Oracle database research.
    
    This class sets up and manages the multi-agent workflow that mimics
    the intelligent database exploration capabilities of GitHub Copilot.
    """
    
    def __init__(self, connection_string: str, debug: bool = False):
        self.connection_string = connection_string
        self.debug = debug
        self.mcp_client = MCPClient(connection_string, debug)
        
        # Initialize agents
        self.planner = PlannerAgent(self.mcp_client)
        self.explorer = ExplorerAgent(self.mcp_client)
        self.query_generator = QueryGeneratorAgent(self.mcp_client)
        self.analyst = AnalystAgent(self.mcp_client)
        self.coordinator = CoordinatorAgent(self.mcp_client)
        
        # Build the graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("explorer", self._explorer_node)
        workflow.add_node("query_generator", self._query_generator_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("coordinator", self._coordinator_node)
        
        # Define the workflow edges
        workflow.set_entry_point("planner")
        
        # Add conditional edges based on next_agent state
        workflow.add_conditional_edges(
            "planner",
            self._route_next_agent,
            {
                "explorer": "explorer",
                "query_generator": "query_generator", 
                "analyst": "analyst",
                "coordinator": "coordinator",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "explorer",
            self._route_next_agent,
            {
                "planner": "planner",
                "query_generator": "query_generator",
                "analyst": "analyst", 
                "coordinator": "coordinator",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "query_generator",
            self._route_next_agent,
            {
                "planner": "planner",
                "explorer": "explorer",
                "analyst": "analyst",
                "coordinator": "coordinator", 
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "analyst",
            self._route_next_agent,
            {
                "planner": "planner",
                "explorer": "explorer",
                "query_generator": "query_generator",
                "coordinator": "coordinator",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "coordinator",
            self._route_next_agent,
            {
                "planner": "planner",
                "explorer": "explorer", 
                "query_generator": "query_generator",
                "analyst": "analyst",
                "END": END
            }
        )
        
        return workflow.compile()
    
    def _route_next_agent(self, state: AgentState) -> str:
        """Route to the next agent based on state."""
        if state.get("is_complete", False):
            logger.info("Workflow complete, ending")
            return "END"
        
        next_agent = state.get("next_agent")
        logger.info(f"Routing to next agent: {next_agent}")
        
        if next_agent:
            if next_agent == AgentRole.EXPLORER:
                return "explorer"
            elif next_agent == AgentRole.QUERY_GENERATOR:
                return "query_generator"
            elif next_agent == AgentRole.ANALYST:
                return "analyst"
            elif next_agent == AgentRole.COORDINATOR:
                return "coordinator"
            elif next_agent == AgentRole.PLANNER:
                return "planner"
        
        logger.info("No next agent specified, ending workflow")
        return "END"
    
    async def _planner_node(self, state: AgentState) -> AgentState:
        """Planner agent node."""
        return await self.planner.process(state)
    
    async def _explorer_node(self, state: AgentState) -> AgentState:
        """Explorer agent node."""
        return await self.explorer.process(state)
    
    async def _query_generator_node(self, state: AgentState) -> AgentState:
        """Query generator agent node."""
        return await self.query_generator.process(state)
    
    async def _analyst_node(self, state: AgentState) -> AgentState:
        """Analyst agent node."""
        return await self.analyst.process(state)
    
    async def _coordinator_node(self, state: AgentState) -> AgentState:
        """Coordinator agent node."""
        return await self.coordinator.process(state)
    
    async def research(self, user_request: str) -> Dict[str, Any]:
        """
        Execute the complete research workflow.
        
        Args:
            user_request: The user's database research request
            
        Returns:
            Complete research results
        """
        console.print(Panel(f"[bold blue]Database Research Request:[/bold blue]\n{user_request}", 
                          title="Oracle Agent Demo"))
        
        # Initialize state
        initial_state = create_initial_state(user_request)
        
        # Start MCP client
        async with self.mcp_client:
            console.print("[yellow]Starting MCP server and agents...[/yellow]")
            
            # Execute the workflow
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Processing research request...", total=None)
                
                try:
                    # Run the workflow
                    final_state = await self.workflow.ainvoke(initial_state)
                    
                    progress.update(task, description="Research complete!")
                    
                    return {
                        "success": True,
                        "final_response": final_state.get("final_response", ""),
                        "conversation_history": final_state.get("conversation_history", []),
                        "query_history": final_state.get("query_history", []),
                        "schema_summary": format_schema_summary(final_state),
                        "completed_tasks": final_state.get("completed_tasks", []),
                        "analysis": final_state.get("current_analysis", {})
                    }
                    
                except Exception as e:
                    progress.update(task, description=f"Error: {e}")
                    logger.error(f"Workflow execution failed: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "final_response": f"Research failed: {e}"
                    }


def display_results(results: Dict[str, Any]) -> None:
    """Display research results in a formatted way."""
    
    if not results.get("success", False):
        console.print(Panel(f"[red]Error:[/red] {results.get('error', 'Unknown error')}", 
                          title="Research Failed"))
        return
    
    # Main response
    if results.get("final_response"):
        console.print(Panel(results["final_response"], title="[green]Research Results[/green]"))
    
    # Show conversation flow
    if results.get("conversation_history"):
        console.print("\n[bold]Agent Conversation Flow:[/bold]")
        for msg in results["conversation_history"]:
            role_color = {
                "agent": "blue",
                "assistant": "green", 
                "user": "yellow"
            }.get(msg.role, "white")
            
            agent_info = f" ({msg.agent_role.value})" if msg.agent_role else ""
            console.print(f"[{role_color}]{msg.role}{agent_info}:[/{role_color}] {msg.content}")
    
    # Show SQL queries executed
    if results.get("query_history"):
        console.print("\n[bold]SQL Queries Executed:[/bold]")
        for i, query in enumerate(results["query_history"], 1):
            if query.error:
                console.print(f"[red]Query {i} (Failed):[/red]")
                console.print(Syntax(query.sql, "sql", theme="monokai"))
                console.print(f"[red]Error: {query.error}[/red]")
            else:
                console.print(f"[green]Query {i} ({query.row_count} rows, {query.execution_time:.3f}s):[/green]")
                console.print(Syntax(query.sql, "sql", theme="monokai"))
                
                # Show sample results
                if query.rows and query.columns:
                    table = Table(title=f"Sample Results (showing first 3 rows)")
                    for col in query.columns:
                        table.add_column(col)
                    
                    for row in query.rows[:3]:
                        table.add_row(*[str(val) for val in row])
                    
                    console.print(table)
            console.print()
    
    # Show schema summary
    if results.get("schema_summary"):
        console.print(Panel(results["schema_summary"], title="[cyan]Database Schema Summary[/cyan]"))
    
    # Show completed tasks
    if results.get("completed_tasks"):
        console.print("\n[bold]Completed Research Tasks:[/bold]")
        for task in results["completed_tasks"]:
            console.print(f"✓ {task.description}")
            if task.results:
                for key, value in task.results.items():
                    console.print(f"  • {key}: {value}")


@app.command()
def demo(
    request: str = typer.Argument(..., help="Database research request"),
    connection_string: str = typer.Option(
        None, 
        "--connection", "-c",
        help="Oracle connection string (or set DB_CONNECTION_STRING env var)"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """
    Run the Oracle database research agent demo.
    
    Examples:
    
    \b
    # Explore database structure
    python -m oracle_mcp_server.langgraph_demo "Show me all the tables in the database"
    
    \b
    # Find specific data
    python -m oracle_mcp_server.langgraph_demo "Find all customers who made orders this year"
    
    \b  
    # Analyze performance
    python -m oracle_mcp_server.langgraph_demo "Analyze the performance of our sales data"
    """
    
    # Get connection string
    if not connection_string:
        connection_string = os.getenv("DB_CONNECTION_STRING")
    
    if not connection_string:
        console.print("[red]Error:[/red] Connection string required. Set DB_CONNECTION_STRING env var or use --connection")
        raise typer.Exit(1)
    
    # Setup logging level
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async def run_demo():
        # Create and run the workflow
        workflow = OracleResearchWorkflow(connection_string, debug)
        results = await workflow.research(request)
        
        # Display results
        display_results(results)
        
        return results
    
    # Run the async workflow
    try:
        results = asyncio.run(run_demo())
        
        if not results.get("success", False):
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Demo failed:[/red] {e}")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command("examples")
def show_examples():
    """Show example research requests that work well with the demo."""
    
    examples = [
        {
            "title": "Database Exploration",
            "requests": [
                "Show me all the tables in the database",
                "What views are available in the database?", 
                "List all stored procedures and functions",
                "Describe the structure of the EMPLOYEES table"
            ]
        },
        {
            "title": "Data Discovery", 
            "requests": [
                "Find all customers in the database",
                "Show me sample data from the orders table",
                "What products do we have in inventory?",
                "Find the most recent transactions"
            ]
        },
        {
            "title": "Business Analysis",
            "requests": [
                "Analyze sales performance by region",
                "Find customers who made large orders",
                "Show me trends in our order data", 
                "Generate a report on customer activity"
            ]
        },
        {
            "title": "Performance Analysis",
            "requests": [
                "Analyze the performance of queries on the sales table",
                "Find tables that might need indexing",
                "Show me execution plans for complex queries",
                "Identify potential performance bottlenecks"
            ]
        }
    ]
    
    console.print(Panel("[bold]Oracle Database Research Agent - Example Requests[/bold]", 
                       title="Examples"))
    
    for category in examples:
        console.print(f"\n[bold cyan]{category['title']}:[/bold cyan]")
        for request in category["requests"]:
            console.print(f"  • {request}")
    
    console.print(f"\n[yellow]Usage:[/yellow]")
    console.print(f"python -m oracle_mcp_server.langgraph_demo \"<your request>\"")
    console.print(f"\n[yellow]Note:[/yellow] Make sure to set DB_CONNECTION_STRING environment variable")


if __name__ == "__main__":
    app()