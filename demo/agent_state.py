#!/usr/bin/env python3
"""
LangGraph agent state management for Oracle database research.

This module defines the state structures and management for the multi-agent
database research system using LangGraph.
"""

from typing import Any, Dict, List, Optional, TypedDict
from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    """Roles for different agents in the system."""
    PLANNER = "planner"
    EXPLORER = "explorer" 
    QUERY_GENERATOR = "query_generator"
    ANALYST = "analyst"
    COORDINATOR = "coordinator"


class TaskStatus(Enum):
    """Status of research tasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DatabaseSchema:
    """Database schema information."""
    tables: List[Dict[str, Any]] = field(default_factory=list)
    views: List[Dict[str, Any]] = field(default_factory=list)
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    table_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class QueryResult:
    """Query execution result."""
    sql: str
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass
class ResearchTask:
    """A research task to be executed."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[AgentRole] = None
    dependencies: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ConversationMessage:
    """A message in the conversation history."""
    role: str  # user, assistant, agent
    content: str
    agent_role: Optional[AgentRole] = None
    timestamp: str = field(default_factory=lambda: "")
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentState(TypedDict):
    """
    State shared across all agents in the LangGraph workflow.
    
    This contains all the information needed for agents to coordinate
    their database research activities.
    """
    # User request and conversation
    user_request: str
    conversation_history: List[ConversationMessage]
    
    # Database schema knowledge
    schema: DatabaseSchema
    
    # Current research context
    current_task: Optional[ResearchTask]
    task_queue: List[ResearchTask]
    completed_tasks: List[ResearchTask]
    
    # Query and analysis results
    query_history: List[QueryResult]
    current_analysis: Dict[str, Any]
    
    # Agent coordination
    next_agent: Optional[AgentRole]
    agent_messages: List[str]
    
    # Final output
    final_response: str
    is_complete: bool


def create_initial_state(user_request: str) -> AgentState:
    """Create initial agent state from user request."""
    return AgentState(
        user_request=user_request,
        conversation_history=[],
        schema=DatabaseSchema(),
        current_task=None,
        task_queue=[],
        completed_tasks=[],
        query_history=[],
        current_analysis={},
        next_agent=AgentRole.PLANNER,
        agent_messages=[],
        final_response="",
        is_complete=False
    )


def add_message(state: AgentState, role: str, content: str, 
                agent_role: Optional[AgentRole] = None, 
                metadata: Optional[Dict[str, Any]] = None) -> None:
    """Add a message to the conversation history."""
    from datetime import datetime
    
    message = ConversationMessage(
        role=role,
        content=content,
        agent_role=agent_role,
        timestamp=datetime.now().isoformat(),
        metadata=metadata or {}
    )
    state["conversation_history"].append(message)


def add_task(state: AgentState, task_id: str, description: str, 
             dependencies: Optional[List[str]] = None) -> None:
    """Add a new research task to the queue."""
    task = ResearchTask(
        id=task_id,
        description=description,
        dependencies=dependencies or []
    )
    state["task_queue"].append(task)


def complete_task(state: AgentState, task_id: str, 
                  results: Dict[str, Any]) -> None:
    """Mark a task as completed with results."""
    # Find and remove from queue
    task = None
    for i, t in enumerate(state["task_queue"]):
        if t.id == task_id:
            task = state["task_queue"].pop(i)
            break
    
    if task:
        task.status = TaskStatus.COMPLETED
        task.results = results
        state["completed_tasks"].append(task)


def add_query_result(state: AgentState, sql: str, result: Dict[str, Any]) -> None:
    """Add a query result to the history."""
    query_result = QueryResult(
        sql=sql,
        columns=result.get("columns", []),
        rows=result.get("rows", []),
        row_count=result.get("row_count", 0),
        execution_time=result.get("execution_time_seconds", 0.0),
        error=result.get("error")
    )
    state["query_history"].append(query_result)


def get_available_tasks(state: AgentState) -> List[ResearchTask]:
    """Get tasks that are ready to be executed (dependencies met)."""
    completed_task_ids = {task.id for task in state["completed_tasks"]}
    
    available = []
    for task in state["task_queue"]:
        if task.status == TaskStatus.PENDING:
            if all(dep in completed_task_ids for dep in task.dependencies):
                available.append(task)
    
    return available


def update_schema_info(state: AgentState, schema_type: str, data: Dict[str, Any]) -> None:
    """Update schema information in the state."""
    if schema_type == "tables":
        state["schema"].tables = data.get("tables", [])
    elif schema_type == "views":
        state["schema"].views = data.get("views", [])
    elif schema_type == "procedures":
        state["schema"].procedures = data.get("procedures", [])
    elif schema_type == "table_details":
        table_name = data.get("table_name")
        if table_name:
            state["schema"].table_details[table_name] = data


def get_relevant_tables(state: AgentState, query_context: str) -> List[Dict[str, Any]]:
    """Get tables that might be relevant to the query context."""
    # Simple keyword matching - could be enhanced with embeddings
    query_lower = query_context.lower()
    relevant = []
    
    for table in state["schema"].tables:
        table_name = table.get("table_name", "").lower()
        table_comment = table.get("table_comment", "").lower()
        
        # Check if query keywords appear in table name or comments
        if any(word in table_name or word in table_comment 
               for word in query_lower.split()):
            relevant.append(table)
    
    return relevant


def format_schema_summary(state: AgentState) -> str:
    """Format a summary of the current schema knowledge."""
    schema = state["schema"]
    
    summary = []
    summary.append(f"Database Schema Summary:")
    summary.append(f"- Tables: {len(schema.tables)}")
    summary.append(f"- Views: {len(schema.views)}")
    summary.append(f"- Procedures: {len(schema.procedures)}")
    summary.append(f"- Detailed table info: {len(schema.table_details)}")
    
    if schema.tables:
        summary.append("\nKey Tables:")
        for table in schema.tables[:5]:  # Show first 5
            name = table.get("table_name", "Unknown")
            comment = table.get("table_comment", "No description")
            summary.append(f"  - {name}: {comment}")
    
    return "\n".join(summary)