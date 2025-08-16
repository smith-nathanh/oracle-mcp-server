#!/usr/bin/env python3
"""
Specialized agents for Oracle database research using LangGraph.

This module implements the individual agents that work together to provide
intelligent database exploration and query generation capabilities.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from demo.agent_state import (
    AgentState, AgentRole, TaskStatus, 
    add_message, add_task, complete_task, add_query_result,
    get_available_tasks, update_schema_info, get_relevant_tables
)
from demo.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Agent responsible for analyzing user requests and creating research plans.
    
    This agent breaks down complex user requests into manageable tasks
    and determines the optimal sequence of database exploration activities.
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.role = AgentRole.PLANNER
    
    async def process(self, state: AgentState) -> AgentState:
        """Analyze user request and create research plan."""
        user_request = state["user_request"]
        
        add_message(state, "agent", f"Planning research for: {user_request}", self.role)
        
        # Analyze the request to determine what we need to discover
        plan = self._analyze_request(user_request)
        
        # Create tasks based on the plan
        for task in plan:
            add_task(state, task["id"], task["description"], task.get("dependencies", []))
        
        # Always start with schema discovery
        if not any(task.id == "discover_schema" for task in state["task_queue"]):
            add_task(state, "discover_schema", "Discover database schema (tables, views, procedures)")
        
        # Set next agent
        state["next_agent"] = AgentRole.EXPLORER
        
        add_message(state, "agent", f"Created {len(plan)} research tasks", self.role)
        
        return state
    
    def _analyze_request(self, request: str) -> List[Dict[str, Any]]:
        """Analyze user request and create task plan."""
        request_lower = request.lower()
        tasks = []
        
        # Common patterns and their corresponding tasks
        if any(word in request_lower for word in ["find", "show", "list", "get"]):
            if any(word in request_lower for word in ["table", "tables"]):
                tasks.append({
                    "id": "find_tables",
                    "description": "Find relevant tables based on request",
                    "dependencies": ["discover_schema"]
                })
            
            if any(word in request_lower for word in ["customer", "order", "product", "sale"]):
                tasks.append({
                    "id": "explore_business_data",
                    "description": "Explore business-related tables and data",
                    "dependencies": ["find_tables"]
                })
        
        if any(word in request_lower for word in ["analyze", "performance", "trend", "report"]):
            tasks.append({
                "id": "generate_analysis_query",
                "description": "Generate analytical queries for data insights",
                "dependencies": ["explore_business_data"]
            })
        
        if any(word in request_lower for word in ["export", "download", "save"]):
            tasks.append({
                "id": "export_results",
                "description": "Export query results in requested format",
                "dependencies": ["generate_analysis_query"]
            })
        
        # Default exploration task if no specific pattern matched
        if not tasks:
            tasks.append({
                "id": "general_exploration",
                "description": "General database exploration to understand structure",
                "dependencies": ["discover_schema"]
            })
        
        return tasks


class ExplorerAgent:
    """
    Agent responsible for database schema discovery and exploration.
    
    This agent uses MCP tools to understand the database structure,
    table relationships, and available data.
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.role = AgentRole.EXPLORER
    
    async def process(self, state: AgentState) -> AgentState:
        """Explore database schema and structure."""
        available_tasks = get_available_tasks(state)
        
        # Look for schema-related tasks
        schema_tasks = [t for t in available_tasks if "schema" in t.description.lower() or "discover" in t.description.lower()]
        
        if schema_tasks:
            task = schema_tasks[0]
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_agent = self.role
            
            add_message(state, "agent", f"Exploring database schema...", self.role)
            
            try:
                # Discover tables
                tables_result = await self.mcp_client.list_tables()
                update_schema_info(state, "tables", tables_result)
                
                # Discover views
                views_result = await self.mcp_client.list_views()
                update_schema_info(state, "views", views_result)
                
                # Discover procedures
                procedures_result = await self.mcp_client.list_procedures()
                update_schema_info(state, "procedures", procedures_result)
                
                # Get details for key tables (limit to avoid overwhelming)
                tables = tables_result.get("tables", [])[:10]
                for table in tables:
                    table_name = table.get("table_name")
                    owner = table.get("owner")
                    if table_name:
                        try:
                            table_details = await self.mcp_client.describe_table(table_name, owner)
                            update_schema_info(state, "table_details", table_details)
                        except Exception as e:
                            logger.warning(f"Could not get details for table {table_name}: {e}")
                
                complete_task(state, task.id, {
                    "tables_found": len(tables_result.get("tables", [])),
                    "views_found": len(views_result.get("views", [])),
                    "procedures_found": len(procedures_result.get("procedures", [])),
                    "detailed_tables": len(state["schema"].table_details)
                })
                
                add_message(state, "agent", 
                          f"Discovered {len(tables_result.get('tables', []))} tables, "
                          f"{len(views_result.get('views', []))} views, "
                          f"{len(procedures_result.get('procedures', []))} procedures", self.role)
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                add_message(state, "agent", f"Schema exploration failed: {e}", self.role)
        
        # Look for table exploration tasks
        explore_tasks = [t for t in available_tasks if "explore" in t.description.lower() and t.id != "discover_schema"]
        
        if explore_tasks:
            task = explore_tasks[0] 
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_agent = self.role
            
            # Find relevant tables based on user request
            relevant_tables = get_relevant_tables(state, state["user_request"])
            
            if relevant_tables:
                add_message(state, "agent", 
                          f"Found {len(relevant_tables)} potentially relevant tables", self.role)
                
                # Sample data from relevant tables
                sample_results = {}
                for table in relevant_tables[:5]:  # Limit to 5 tables
                    table_name = table.get("table_name")
                    owner = table.get("owner")
                    
                    try:
                        # Generate and execute sample query
                        samples = await self.mcp_client.generate_sample_queries(table_name, owner)
                        if samples and "sample_queries" in samples:
                            first_query = samples["sample_queries"][0]
                            # Extract SQL from comment format
                            sql_match = re.search(r'SELECT.*?;', first_query, re.DOTALL | re.IGNORECASE)
                            if sql_match:
                                sql = sql_match.group(0)
                                result = await self.mcp_client.execute_query(sql)
                                add_query_result(state, sql, result)
                                sample_results[table_name] = result
                    except Exception as e:
                        logger.warning(f"Could not sample table {table_name}: {e}")
                
                complete_task(state, task.id, {
                    "relevant_tables": [t.get("table_name") for t in relevant_tables],
                    "sampled_tables": list(sample_results.keys())
                })
            else:
                add_message(state, "agent", "No obviously relevant tables found, will explore top tables", self.role)
                complete_task(state, task.id, {"relevant_tables": []})
        
        # Determine next agent
        remaining_tasks = get_available_tasks(state)
        if any("query" in t.description.lower() or "generate" in t.description.lower() for t in remaining_tasks):
            state["next_agent"] = AgentRole.QUERY_GENERATOR
        elif any("analysis" in t.description.lower() for t in remaining_tasks):
            state["next_agent"] = AgentRole.ANALYST
        else:
            state["next_agent"] = AgentRole.COORDINATOR
        
        return state


class QueryGeneratorAgent:
    """
    Agent responsible for generating SQL queries based on user requests.
    
    This agent uses schema knowledge to create appropriate queries
    that answer the user's questions.
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.role = AgentRole.QUERY_GENERATOR
    
    async def process(self, state: AgentState) -> AgentState:
        """Generate and execute queries based on user request."""
        available_tasks = get_available_tasks(state)
        
        # Look for query generation tasks
        query_tasks = [t for t in available_tasks if "query" in t.description.lower() or "generate" in t.description.lower()]
        
        if query_tasks:
            task = query_tasks[0]
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_agent = self.role
            
            add_message(state, "agent", "Generating queries based on request and schema...", self.role)
            
            try:
                # Generate queries based on user request and available schema
                queries = self._generate_queries(state)
                
                executed_queries = []
                for query_info in queries:
                    sql = query_info["sql"]
                    description = query_info["description"]
                    
                    try:
                        add_message(state, "agent", f"Executing: {description}", self.role)
                        result = await self.mcp_client.execute_query(sql)
                        add_query_result(state, sql, result)
                        executed_queries.append({
                            "sql": sql,
                            "description": description,
                            "rows": result.get("row_count", 0)
                        })
                        
                        # Also get execution plan for performance insights
                        if "SELECT" in sql.upper():
                            try:
                                plan = await self.mcp_client.explain_query(sql)
                                # Store plan in current analysis
                                if "execution_plans" not in state["current_analysis"]:
                                    state["current_analysis"]["execution_plans"] = []
                                state["current_analysis"]["execution_plans"].append({
                                    "sql": sql,
                                    "plan": plan
                                })
                            except Exception as e:
                                logger.warning(f"Could not get execution plan: {e}")
                        
                    except Exception as e:
                        add_message(state, "agent", f"Query failed: {e}", self.role)
                        executed_queries.append({
                            "sql": sql,
                            "description": description,
                            "error": str(e)
                        })
                
                complete_task(state, task.id, {
                    "queries_generated": len(queries),
                    "queries_executed": len(executed_queries),
                    "successful_queries": len([q for q in executed_queries if "error" not in q])
                })
                
                add_message(state, "agent", 
                          f"Generated and executed {len(executed_queries)} queries", self.role)
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                add_message(state, "agent", f"Query generation failed: {e}", self.role)
        
        # Determine next agent
        remaining_tasks = get_available_tasks(state)
        if any("analysis" in t.description.lower() or "export" in t.description.lower() for t in remaining_tasks):
            state["next_agent"] = AgentRole.ANALYST
        else:
            state["next_agent"] = AgentRole.COORDINATOR
        
        return state
    
    def _generate_queries(self, state: AgentState) -> List[Dict[str, str]]:
        """Generate appropriate queries based on state and user request."""
        queries = []
        user_request = state["user_request"].lower()
        schema = state["schema"]
        
        # If we have relevant tables from exploration, use them
        relevant_tables = []
        for task in state["completed_tasks"]:
            if "relevant_tables" in task.results:
                relevant_tables.extend(task.results["relevant_tables"])
        
        # If no relevant tables found, use the first few available tables
        if not relevant_tables and schema.tables:
            relevant_tables = [t.get("table_name") for t in schema.tables[:3]]
        
        # Generate queries based on request type
        if any(word in user_request for word in ["find", "show", "list"]):
            # Simple data retrieval queries
            for table_name in relevant_tables[:3]:
                table_details = schema.table_details.get(table_name)
                if table_details:
                    owner = table_details.get("owner")
                    table_ref = f"{owner}.{table_name}" if owner else table_name
                    
                    queries.append({
                        "sql": f"SELECT * FROM {table_ref} WHERE ROWNUM <= 10",
                        "description": f"Sample data from {table_name}"
                    })
        
        if any(word in user_request for word in ["count", "how many", "total"]):
            # Count queries
            for table_name in relevant_tables[:3]:
                table_details = schema.table_details.get(table_name)
                if table_details:
                    owner = table_details.get("owner")
                    table_ref = f"{owner}.{table_name}" if owner else table_name
                    
                    queries.append({
                        "sql": f"SELECT COUNT(*) as total_rows FROM {table_ref}",
                        "description": f"Count of rows in {table_name}"
                    })
        
        if any(word in user_request for word in ["recent", "latest", "new"]):
            # Recent data queries (look for date columns)
            for table_name in relevant_tables[:2]:
                table_details = schema.table_details.get(table_name)
                if table_details and "columns" in table_details:
                    date_columns = [
                        col["column_name"] for col in table_details["columns"]
                        if col["data_type"] in ["DATE", "TIMESTAMP"]
                    ]
                    if date_columns:
                        owner = table_details.get("owner")
                        table_ref = f"{owner}.{table_name}" if owner else table_name
                        date_col = date_columns[0]
                        
                        queries.append({
                            "sql": f"SELECT * FROM {table_ref} ORDER BY {date_col} DESC FETCH FIRST 10 ROWS ONLY",
                            "description": f"Most recent records from {table_name}"
                        })
        
        # If no specific queries generated, create basic exploration queries
        if not queries and relevant_tables:
            table_name = relevant_tables[0]
            table_details = schema.table_details.get(table_name)
            if table_details:
                owner = table_details.get("owner")
                table_ref = f"{owner}.{table_name}" if owner else table_name
                
                queries.append({
                    "sql": f"SELECT * FROM {table_ref} WHERE ROWNUM <= 5",
                    "description": f"Sample data from {table_name}"
                })
        
        return queries


class AnalystAgent:
    """
    Agent responsible for analyzing query results and providing insights.
    
    This agent interprets the data retrieved by queries and formats
    it into meaningful insights for the user.
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.role = AgentRole.ANALYST
    
    async def process(self, state: AgentState) -> AgentState:
        """Analyze query results and provide insights."""
        available_tasks = get_available_tasks(state)
        
        # Look for analysis tasks
        analysis_tasks = [t for t in available_tasks if "analysis" in t.description.lower()]
        export_tasks = [t for t in available_tasks if "export" in t.description.lower()]
        
        if analysis_tasks or export_tasks:
            task = (analysis_tasks + export_tasks)[0]
            task.status = TaskStatus.IN_PROGRESS
            task.assigned_agent = self.role
            
            add_message(state, "agent", "Analyzing query results...", self.role)
            
            try:
                # Analyze the query results
                analysis = self._analyze_results(state)
                state["current_analysis"].update(analysis)
                
                # Handle export if requested
                if export_tasks and state["query_history"]:
                    last_query = state["query_history"][-1]
                    if not last_query.error:
                        export_result = await self.mcp_client.export_query_results(
                            last_query.sql, "csv"
                        )
                        analysis["export_data"] = export_result
                
                complete_task(state, task.id, analysis)
                
                add_message(state, "agent", 
                          f"Analysis complete. Found insights about {len(state['query_history'])} queries.", self.role)
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                add_message(state, "agent", f"Analysis failed: {e}", self.role)
        
        state["next_agent"] = AgentRole.COORDINATOR
        
        return state
    
    def _analyze_results(self, state: AgentState) -> Dict[str, Any]:
        """Analyze query results and generate insights."""
        analysis = {}
        
        if not state["query_history"]:
            return {"message": "No query results to analyze"}
        
        # Summarize query results
        total_queries = len(state["query_history"])
        successful_queries = len([q for q in state["query_history"] if not q.error])
        total_rows = sum(q.row_count for q in state["query_history"] if not q.error)
        
        analysis["summary"] = {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "total_rows_retrieved": total_rows,
            "avg_execution_time": sum(q.execution_time for q in state["query_history"]) / total_queries if total_queries > 0 else 0
        }
        
        # Analyze data patterns
        patterns = []
        for query_result in state["query_history"]:
            if not query_result.error and query_result.rows:
                # Look for interesting patterns in the data
                if query_result.row_count > 0:
                    patterns.append(f"Query returned {query_result.row_count} rows")
                    
                    # Check for potential interesting columns
                    if query_result.columns:
                        interesting_cols = [col for col in query_result.columns 
                                          if any(keyword in col.lower() for keyword in 
                                                ["id", "name", "date", "amount", "count", "total"])]
                        if interesting_cols:
                            patterns.append(f"Found key columns: {', '.join(interesting_cols)}")
        
        analysis["data_patterns"] = patterns
        
        # Performance insights
        if "execution_plans" in state["current_analysis"]:
            performance_notes = []
            for plan_info in state["current_analysis"]["execution_plans"]:
                plan = plan_info.get("plan", {})
                if isinstance(plan, dict) and "execution_plan" in plan:
                    plan_steps = plan["execution_plan"]
                    if plan_steps:
                        # Look for full table scans or other performance indicators
                        has_full_scan = any("TABLE ACCESS FULL" in str(step.get("operation", "")) 
                                          for step in plan_steps)
                        if has_full_scan:
                            performance_notes.append("Query uses full table scan - consider indexing")
            
            analysis["performance_insights"] = performance_notes
        
        return analysis


class CoordinatorAgent:
    """
    Agent responsible for coordinating the overall workflow and generating final responses.
    
    This agent determines when the research is complete and formats
    the final response for the user.
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.role = AgentRole.COORDINATOR
    
    async def process(self, state: AgentState) -> AgentState:
        """Coordinate workflow and generate final response."""
        
        # Check if all tasks are complete
        remaining_tasks = get_available_tasks(state)
        
        if remaining_tasks:
            # Still have work to do, delegate to appropriate agent
            next_task = remaining_tasks[0]
            
            if "schema" in next_task.description.lower() or "discover" in next_task.description.lower():
                state["next_agent"] = AgentRole.EXPLORER
            elif "query" in next_task.description.lower() or "generate" in next_task.description.lower():
                state["next_agent"] = AgentRole.QUERY_GENERATOR
            elif "analysis" in next_task.description.lower() or "export" in next_task.description.lower():
                state["next_agent"] = AgentRole.ANALYST
            else:
                # Handle unknown task type
                add_message(state, "agent", f"Completing remaining task: {next_task.description}", self.role)
                complete_task(state, next_task.id, {"status": "completed_by_coordinator"})
                # Check for more tasks after completing this one
                remaining_after = get_available_tasks(state)
                if remaining_after:
                    state["next_agent"] = AgentRole.COORDINATOR
                else:
                    # No more tasks, finish up
                    final_response = self._generate_final_response(state)
                    state["final_response"] = final_response
                    state["is_complete"] = True
                    state["next_agent"] = None
                    add_message(state, "assistant", final_response, self.role)
        else:
            # All tasks complete, generate final response
            final_response = self._generate_final_response(state)
            state["final_response"] = final_response
            state["is_complete"] = True
            state["next_agent"] = None
            
            add_message(state, "assistant", final_response, self.role)
        
        return state
    
    def _generate_final_response(self, state: AgentState) -> str:
        """Generate the final response based on all completed work."""
        response_parts = []
        
        # Start with summary of what was accomplished
        completed_tasks = state["completed_tasks"]
        if completed_tasks:
            response_parts.append(f"I completed {len(completed_tasks)} research tasks to answer your request:")
            for task in completed_tasks:
                response_parts.append(f"✓ {task.description}")
        
        # Schema information
        schema = state["schema"]
        if schema.tables:
            response_parts.append(f"\nDatabase Overview:")
            response_parts.append(f"- Found {len(schema.tables)} tables, {len(schema.views)} views, {len(schema.procedures)} procedures")
            
            if schema.table_details:
                response_parts.append(f"- Analyzed {len(schema.table_details)} tables in detail")
        
        # Query results
        if state["query_history"]:
            successful_queries = [q for q in state["query_history"] if not q.error]
            if successful_queries:
                response_parts.append(f"\nQuery Results:")
                response_parts.append(f"- Executed {len(successful_queries)} successful queries")
                response_parts.append(f"- Retrieved {sum(q.row_count for q in successful_queries)} total rows")
                
                # Show sample of interesting results
                for i, query_result in enumerate(successful_queries[:3]):
                    response_parts.append(f"\nQuery {i+1}: {query_result.sql}")
                    response_parts.append(f"  → {query_result.row_count} rows in {query_result.execution_time:.3f}s")
                    
                    if query_result.rows and query_result.columns:
                        # Show first few rows
                        response_parts.append(f"  Sample data:")
                        response_parts.append(f"    Columns: {', '.join(query_result.columns)}")
                        for row_idx, row in enumerate(query_result.rows[:3]):
                            row_str = ', '.join(str(val) for val in row)
                            response_parts.append(f"    Row {row_idx+1}: {row_str}")
        
        # Analysis insights
        if state["current_analysis"]:
            analysis = state["current_analysis"]
            
            if "summary" in analysis:
                summary = analysis["summary"]
                response_parts.append(f"\nPerformance Summary:")
                response_parts.append(f"- Average query time: {summary.get('avg_execution_time', 0):.3f}s")
                response_parts.append(f"- Total data retrieved: {summary.get('total_rows_retrieved', 0)} rows")
            
            if "data_patterns" in analysis and analysis["data_patterns"]:
                response_parts.append(f"\nData Insights:")
                for pattern in analysis["data_patterns"]:
                    response_parts.append(f"- {pattern}")
            
            if "performance_insights" in analysis and analysis["performance_insights"]:
                response_parts.append(f"\nPerformance Notes:")
                for insight in analysis["performance_insights"]:
                    response_parts.append(f"- {insight}")
        
        # Export information
        if "export_data" in state["current_analysis"]:
            response_parts.append(f"\nData Export:")
            response_parts.append(f"- Results exported in CSV format")
        
        if not response_parts:
            return "I explored your database but didn't find specific results matching your request. The database structure has been analyzed and is ready for more targeted queries."
        
        return "\n".join(response_parts)