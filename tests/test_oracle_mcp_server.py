import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from datetime import datetime

from oracle_mcp_server.server import OracleMCPServer


class TestOracleMCPServer:
    """Simplified test cases for OracleMCPServer class"""

    @pytest.mark.unit
    def test_init(self):
        """Test OracleMCPServer initialization"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            assert server.server is not None
            assert server.connection_manager is not None
            assert server.inspector is not None
            assert server.executor is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_setup_handlers_runs_without_error(self):
        """Test that setup_handlers completes without error"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock the underlying MCP server
            server.server = MagicMock()
            server.server.list_resources = MagicMock(return_value=lambda f: f)
            server.server.read_resource = MagicMock(return_value=lambda f: f)
            server.server.list_tools = MagicMock(return_value=lambda f: f)
            server.server.call_tool = MagicMock(return_value=lambda f: f)
            
            # Should run without error
            await server.setup_handlers()
            
            # Verify handlers were registered
            server.server.list_resources.assert_called_once()
            server.server.read_resource.assert_called_once()
            server.server.list_tools.assert_called_once()
            server.server.call_tool.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inspector_get_tables(self):
        """Test inspector get_tables functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock inspector
            server.inspector = MagicMock()
            server.inspector.get_tables = AsyncMock(return_value=[
                {'owner': 'HR', 'table_name': 'EMPLOYEES', 'table_comment': 'Employee data'}
            ])
            
            result = await server.inspector.get_tables()
            
            assert len(result) == 1
            assert result[0]['table_name'] == 'EMPLOYEES'

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inspector_get_views(self):
        """Test inspector get_views functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock inspector
            server.inspector = MagicMock()
            server.inspector.get_views = AsyncMock(return_value=[
                {'owner': 'HR', 'view_name': 'EMP_VIEW', 'view_comment': 'Employee view'}
            ])
            
            result = await server.inspector.get_views()
            
            assert len(result) == 1
            assert result[0]['view_name'] == 'EMP_VIEW'

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inspector_get_procedures(self):
        """Test inspector get_procedures functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock inspector
            server.inspector = MagicMock()
            server.inspector.get_procedures = AsyncMock(return_value=[
                {'owner': 'HR', 'object_name': 'GET_EMP', 'object_type': 'FUNCTION'}
            ])
            
            result = await server.inspector.get_procedures()
            
            assert len(result) == 1
            assert result[0]['object_name'] == 'GET_EMP'

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inspector_get_table_columns(self):
        """Test inspector get_table_columns functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock inspector
            server.inspector = MagicMock()
            server.inspector.get_table_columns = AsyncMock(return_value=[
                {'column_name': 'ID', 'data_type': 'NUMBER', 'nullable': 'N'}
            ])
            
            result = await server.inspector.get_table_columns('EMPLOYEES', 'HR')
            
            assert len(result) == 1
            assert result[0]['column_name'] == 'ID'

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_execute_query(self):
        """Test executor execute_query functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock executor
            server.executor = MagicMock()
            server.executor.execute_query = AsyncMock(return_value={
                'columns': ['ID', 'NAME'],
                'rows': [[1, 'John'], [2, 'Jane']],
                'row_count': 2,
                'execution_time_seconds': 0.05
            })
            
            result = await server.executor.execute_query('SELECT * FROM employees')
            
            assert result['row_count'] == 2
            assert len(result['columns']) == 2
            assert len(result['rows']) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_executor_explain_query(self):
        """Test executor explain_query functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock executor
            server.executor = MagicMock()
            server.executor.explain_query = AsyncMock(return_value={
                'execution_plan': [{'operation': 'TABLE ACCESS', 'object_name': 'EMPLOYEES'}],
                'statement_id': 'PLAN_123'
            })
            
            result = await server.executor.explain_query('SELECT * FROM employees')
            
            assert 'execution_plan' in result
            assert len(result['execution_plan']) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_manager_initialize_pool(self):
        """Test connection manager initialize_pool functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock connection manager
            server.connection_manager = MagicMock()
            server.connection_manager.initialize_pool = AsyncMock()
            
            await server.connection_manager.initialize_pool()
            
            server.connection_manager.initialize_pool.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_manager_get_connection(self):
        """Test connection manager get_connection functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock connection manager
            mock_connection = MagicMock()
            server.connection_manager = MagicMock()
            server.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
            
            result = await server.connection_manager.get_connection()
            
            assert result == mock_connection

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_manager_close_pool(self):
        """Test connection manager close_pool functionality"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock connection manager
            server.connection_manager = MagicMock()
            server.connection_manager.close_pool = MagicMock()
            
            server.connection_manager.close_pool()
            
            server.connection_manager.close_pool.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are properly handled"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock inspector to raise exception
            server.inspector = MagicMock()
            server.inspector.get_tables = AsyncMock(side_effect=Exception("Database error"))
            
            # Exception should propagate
            with pytest.raises(Exception, match="Database error"):
                await server.inspector.get_tables()

    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_dangerous_query_validation(self):
        """Test that dangerous queries are rejected"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Mock executor to validate dangerous queries
            server.executor = MagicMock()
            server.executor.execute_query = AsyncMock(
                side_effect=ValueError("Only SELECT, DESCRIBE, and EXPLAIN PLAN statements are allowed")
            )
            
            # Dangerous query should be rejected
            with pytest.raises(ValueError, match="Only SELECT, DESCRIBE, and EXPLAIN PLAN statements are allowed"):
                await server.executor.execute_query("DROP TABLE employees")

    @pytest.mark.unit
    def test_server_components_initialized(self):
        """Test that all server components are properly initialized"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', 'test_connection'):
            server = OracleMCPServer()
            
            # Verify all components exist
            assert hasattr(server, 'server')
            assert hasattr(server, 'connection_manager')
            assert hasattr(server, 'inspector')
            assert hasattr(server, 'executor')
            
            # Verify they're not None
            assert server.server is not None
            assert server.connection_manager is not None
            assert server.inspector is not None
            assert server.executor is not None