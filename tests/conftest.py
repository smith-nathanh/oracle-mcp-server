import asyncio
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, Mock
from typing import AsyncGenerator, Dict, Any, List

import oracledb
from oracle_mcp_server.server import (
    OracleConnection,
    DatabaseInspector,
    QueryExecutor,
    OracleMCPServer,
)


@pytest.fixture
def mock_cursor():
    """Create a mock cursor for database operations"""
    cursor = MagicMock()
    cursor.execute = MagicMock()
    cursor.fetchall = MagicMock(return_value=[])
    cursor.description = None
    cursor.close = MagicMock()
    return cursor


@pytest.fixture
def mock_connection():
    """Create a mock Oracle connection"""
    connection = MagicMock()
    connection.cursor = MagicMock()
    connection.close = MagicMock()
    connection.commit = MagicMock()
    return connection


@pytest.fixture
def mock_connection_pool():
    """Create a mock connection pool"""
    pool = MagicMock()
    pool.acquire = MagicMock()
    pool.close = MagicMock()
    return pool


@pytest_asyncio.fixture
async def oracle_connection(mock_connection_pool, mock_connection):
    """Create an OracleConnection instance with mocked dependencies"""
    connection_string = "testuser/testpass@localhost:1521/testdb"
    oracle_conn = OracleConnection(connection_string)
    
    # Mock the pool creation
    with pytest.MonkeyPatch.context() as m:
        m.setattr(oracledb, "create_pool", MagicMock(return_value=mock_connection_pool))
        await oracle_conn.initialize_pool()
    
    # Mock the connection acquisition
    mock_connection_pool.acquire.return_value = mock_connection
    
    return oracle_conn


@pytest_asyncio.fixture
async def database_inspector(oracle_connection):
    """Create a DatabaseInspector instance with mocked dependencies"""
    return DatabaseInspector(oracle_connection)


@pytest_asyncio.fixture
async def query_executor(oracle_connection):
    """Create a QueryExecutor instance with mocked dependencies"""
    return QueryExecutor(oracle_connection)


@pytest.fixture
def sample_table_data():
    """Sample table data for testing"""
    return [
        ("HR", "EMPLOYEES", 100, None, "Employee table", "USERS"),
        ("HR", "DEPARTMENTS", 10, None, "Department table", "USERS"),
        ("HR", "JOBS", 19, None, "Job table", "USERS"),
    ]


@pytest.fixture
def sample_column_data():
    """Sample column data for testing"""
    return [
        ("EMPLOYEE_ID", "NUMBER", 22, 6, 0, "N", None, "Employee ID", 1),
        ("FIRST_NAME", "VARCHAR2", 20, None, None, "Y", None, "First name", 2),
        ("LAST_NAME", "VARCHAR2", 25, None, None, "N", None, "Last name", 3),
        ("EMAIL", "VARCHAR2", 25, None, None, "N", None, "Email address", 4),
        ("HIRE_DATE", "DATE", 7, None, None, "N", None, "Hire date", 5),
    ]


@pytest.fixture
def sample_view_data():
    """Sample view data for testing"""
    return [
        ("HR", "EMP_DETAILS_VIEW", "Employee details view"),
        ("HR", "DEPT_SUMMARY_VIEW", "Department summary view"),
    ]


@pytest.fixture
def sample_procedure_data():
    """Sample procedure data for testing"""
    from datetime import datetime
    test_date = datetime(2023, 1, 1, 10, 30, 45)
    return [
        ("HR", "ADD_EMPLOYEE", "PROCEDURE", "VALID", test_date, test_date),
        ("HR", "GET_EMPLOYEE_COUNT", "FUNCTION", "VALID", test_date, test_date),
        ("HR", "EMP_PACKAGE", "PACKAGE", "VALID", test_date, test_date),
    ]


@pytest.fixture
def sample_query_result():
    """Sample query result for testing"""
    return {
        "columns": ["EMPLOYEE_ID", "FIRST_NAME", "LAST_NAME"],
        "rows": [
            [1, "John", "Doe"],
            [2, "Jane", "Smith"],
            [3, "Bob", "Johnson"],
        ],
        "row_count": 3,
        "execution_time_seconds": 0.05,
        "query": "SELECT EMPLOYEE_ID, FIRST_NAME, LAST_NAME FROM EMPLOYEES WHERE ROWNUM <= 100",
    }


@pytest.fixture
def sample_execution_plan():
    """Sample execution plan for testing"""
    return [
        {
            "operation": "SELECT STATEMENT",
            "object_name": None,
            "cost": 100,
            "cardinality": 1000,
            "bytes": 50000,
        },
        {
            "operation": "  TABLE ACCESS FULL",
            "object_name": "EMPLOYEES",
            "cost": 100,
            "cardinality": 1000,
            "bytes": 50000,
        },
    ]


@pytest.fixture
def mock_env_vars():
    """Mock environment variables"""
    return {
        "DB_CONNECTION_STRING": "testuser/testpass@localhost:1521/testdb",
        "QUERY_LIMIT_SIZE": "100",
        "MAX_ROWS_EXPORT": "10000",
        "TABLE_WHITE_LIST": "EMPLOYEES,DEPARTMENTS",
        "COLUMN_WHITE_LIST": "EMPLOYEES.EMPLOYEE_ID,EMPLOYEES.FIRST_NAME",
        "DEBUG": "False",
    }


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing"""
    server = MagicMock()
    
    # Mock decorators to return a function that can be called
    def mock_decorator(func):
        return func
    
    server.list_resources = MagicMock(return_value=mock_decorator)
    server.read_resource = MagicMock(return_value=mock_decorator)
    server.list_tools = MagicMock(return_value=mock_decorator)
    server.call_tool = MagicMock(return_value=mock_decorator)
    server.get_capabilities = MagicMock()
    server.run = AsyncMock()
    return server


@pytest_asyncio.fixture
async def oracle_mcp_server(mock_mcp_server):
    """Create an OracleMCPServer instance with mocked dependencies"""
    with pytest.MonkeyPatch.context() as m:
        m.setattr("oracle_mcp_server.server.Server", MagicMock(return_value=mock_mcp_server))
        m.setattr("oracle_mcp_server.server.DB_CONNECTION_STRING", "testuser/testpass@localhost:1521/testdb")
        
        server = OracleMCPServer()
        
        # Mock the connection manager
        server.connection_manager = MagicMock()
        server.connection_manager.initialize_pool = AsyncMock()
        server.connection_manager.get_connection = AsyncMock()
        server.connection_manager.close_pool = MagicMock()
        
        return server


@pytest.fixture(autouse=True)
def mock_environment(mock_env_vars):
    """Automatically mock environment variables for all tests"""
    with pytest.MonkeyPatch.context() as m:
        for key, value in mock_env_vars.items():
            m.setenv(key, value)
        yield


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()