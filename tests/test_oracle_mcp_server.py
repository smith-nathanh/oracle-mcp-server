import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from datetime import datetime

from oracle_mcp_server.server import OracleMCPServer
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl


class TestOracleMCPServer:
    """Test cases for OracleMCPServer class"""

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
    async def test_setup_handlers(self, oracle_mcp_server):
        """Test that handlers are set up correctly"""
        await oracle_mcp_server.setup_handlers()
        
        # Verify that handlers were registered
        oracle_mcp_server.server.list_resources.assert_called_once()
        oracle_mcp_server.server.read_resource.assert_called_once()
        oracle_mcp_server.server.list_tools.assert_called_once()
        oracle_mcp_server.server.call_tool.assert_called_once()

    @pytest.mark.unit
    async def test_list_resources_success(self, oracle_mcp_server, sample_table_data):
        """Test successful resource listing"""
        # Mock the inspector to return sample data
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_tables = AsyncMock(return_value=[
            {
                'owner': 'HR',
                'table_name': 'EMPLOYEES',
                'num_rows': 100,
                'last_analyzed': None,
                'table_comment': 'Employee table',
                'tablespace_name': 'USERS'
            }
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.list_resources.call_args[0][0]
        
        # Call the handler
        resources = await handler()
        
        assert len(resources) >= 1
        assert isinstance(resources[0], Resource)
        assert str(resources[0].uri) == "oracle://schema/overview"
        assert resources[0].name == "Database Schema Overview"

    @pytest.mark.unit
    async def test_list_resources_exception_handling(self, oracle_mcp_server):
        """Test resource listing with exception handling"""
        # Mock the inspector to raise an exception
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_tables = AsyncMock(side_effect=Exception("Database error"))
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.list_resources.call_args[0][0]
        
        # Call the handler - should not raise exception
        resources = await handler()
        
        assert resources == []

    @pytest.mark.unit
    async def test_read_resource_schema_overview(self, oracle_mcp_server):
        """Test reading schema overview resource"""
        # Mock the inspector methods
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_tables = AsyncMock(return_value=[{'owner': 'HR', 'table_name': 'EMPLOYEES'}])
        oracle_mcp_server.inspector.get_views = AsyncMock(return_value=[{'owner': 'HR', 'view_name': 'EMP_VIEW'}])
        oracle_mcp_server.inspector.get_procedures = AsyncMock(return_value=[{'owner': 'HR', 'object_name': 'ADD_EMP'}])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.read_resource.call_args[0][0]
        
        # Call the handler
        result = await handler(AnyUrl("oracle://schema/overview"))
        
        data = json.loads(result)
        assert data['database_type'] == 'Oracle'
        assert data['table_count'] == 1
        assert data['view_count'] == 1
        assert data['procedure_count'] == 1
        assert 'generated_at' in data

    @pytest.mark.unit
    async def test_read_resource_table_info(self, oracle_mcp_server, sample_column_data):
        """Test reading table information resource"""
        # Mock the inspector method
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_table_columns = AsyncMock(return_value=[
            {
                'column_name': 'EMPLOYEE_ID',
                'data_type': 'NUMBER',
                'nullable': 'N',
                'column_comment': 'Employee ID'
            }
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.read_resource.call_args[0][0]
        
        # Call the handler
        result = await handler(AnyUrl("oracle://table/HR.EMPLOYEES"))
        
        data = json.loads(result)
        assert data['owner'] == 'HR'
        assert data['table_name'] == 'EMPLOYEES'
        assert data['column_count'] == 1
        assert len(data['columns']) == 1
        assert 'generated_at' in data

    @pytest.mark.unit
    async def test_read_resource_table_info_no_owner(self, oracle_mcp_server):
        """Test reading table information resource without owner"""
        # Mock the inspector method
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_table_columns = AsyncMock(return_value=[])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.read_resource.call_args[0][0]
        
        # Call the handler
        result = await handler(AnyUrl("oracle://table/EMPLOYEES"))
        
        data = json.loads(result)
        assert data['owner'] is None
        assert data['table_name'] == 'EMPLOYEES'

    @pytest.mark.unit
    async def test_read_resource_unknown_uri(self, oracle_mcp_server):
        """Test reading unknown resource URI"""
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.read_resource.call_args[0][0]
        
        # Call the handler with unknown URI
        with pytest.raises(ValueError, match="Unknown resource URI"):
            await handler(AnyUrl("oracle://unknown/resource"))

    @pytest.mark.unit
    async def test_list_tools(self, oracle_mcp_server):
        """Test tool listing"""
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.list_tools.call_args[0][0]
        
        # Call the handler
        tools = await handler()
        
        assert len(tools) == 8
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            'execute_query', 'describe_table', 'list_tables', 'list_views',
            'list_procedures', 'explain_query', 'generate_sample_queries', 'export_query_results'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.unit
    async def test_call_tool_execute_query(self, oracle_mcp_server, sample_query_result):
        """Test calling execute_query tool"""
        # Mock the executor
        oracle_mcp_server.executor = MagicMock()
        oracle_mcp_server.executor.execute_query = AsyncMock(return_value=sample_query_result)
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('execute_query', {'sql': 'SELECT * FROM employees'})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert data['row_count'] == 3
        assert len(data['columns']) == 3

    @pytest.mark.unit
    async def test_call_tool_describe_table(self, oracle_mcp_server, sample_column_data):
        """Test calling describe_table tool"""
        # Mock the inspector
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_table_columns = AsyncMock(return_value=[
            {
                'column_name': 'EMPLOYEE_ID',
                'data_type': 'NUMBER',
                'nullable': 'N'
            }
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('describe_table', {'table_name': 'EMPLOYEES'})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert data['table_name'] == 'EMPLOYEES'
        assert data['column_count'] == 1

    @pytest.mark.unit
    async def test_call_tool_list_tables(self, oracle_mcp_server, sample_table_data):
        """Test calling list_tables tool"""
        # Mock the inspector
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_tables = AsyncMock(return_value=[
            {'owner': 'HR', 'table_name': 'EMPLOYEES'}
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('list_tables', {})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert 'tables' in data
        assert len(data['tables']) == 1

    @pytest.mark.unit
    async def test_call_tool_list_views(self, oracle_mcp_server, sample_view_data):
        """Test calling list_views tool"""
        # Mock the inspector
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_views = AsyncMock(return_value=[
            {'owner': 'HR', 'view_name': 'EMP_VIEW'}
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('list_views', {})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert 'views' in data
        assert len(data['views']) == 1

    @pytest.mark.unit
    async def test_call_tool_list_procedures(self, oracle_mcp_server, sample_procedure_data):
        """Test calling list_procedures tool"""
        # Mock the inspector
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_procedures = AsyncMock(return_value=[
            {'owner': 'HR', 'object_name': 'ADD_EMP', 'object_type': 'PROCEDURE'}
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('list_procedures', {})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert 'procedures' in data
        assert len(data['procedures']) == 1

    @pytest.mark.unit
    async def test_call_tool_explain_query(self, oracle_mcp_server, sample_execution_plan):
        """Test calling explain_query tool"""
        # Mock the executor
        oracle_mcp_server.executor = MagicMock()
        oracle_mcp_server.executor.explain_query = AsyncMock(return_value={
            'execution_plan': sample_execution_plan,
            'statement_id': 'MCP_EXPLAIN_123'
        })
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('explain_query', {'sql': 'SELECT * FROM employees'})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert 'execution_plan' in data
        assert len(data['execution_plan']) == 2

    @pytest.mark.unit
    async def test_call_tool_generate_sample_queries(self, oracle_mcp_server, sample_column_data):
        """Test calling generate_sample_queries tool"""
        # Mock the inspector
        oracle_mcp_server.inspector = MagicMock()
        oracle_mcp_server.inspector.get_table_columns = AsyncMock(return_value=[
            {
                'column_name': 'EMPLOYEE_ID',
                'data_type': 'NUMBER',
            },
            {
                'column_name': 'FIRST_NAME',
                'data_type': 'VARCHAR2',
            }
        ])
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('generate_sample_queries', {'table_name': 'EMPLOYEES'})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert 'sample_queries' in data
        assert len(data['sample_queries']) > 0

    @pytest.mark.unit
    async def test_call_tool_export_query_results_json(self, oracle_mcp_server, sample_query_result):
        """Test calling export_query_results tool with JSON format"""
        # Mock the executor
        oracle_mcp_server.executor = MagicMock()
        oracle_mcp_server.executor.execute_query = AsyncMock(return_value=sample_query_result)
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('export_query_results', {
            'sql': 'SELECT * FROM employees',
            'format': 'json'
        })
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert data['row_count'] == 3

    @pytest.mark.unit
    async def test_call_tool_export_query_results_csv(self, oracle_mcp_server, sample_query_result):
        """Test calling export_query_results tool with CSV format"""
        # Mock the executor
        oracle_mcp_server.executor = MagicMock()
        oracle_mcp_server.executor.execute_query = AsyncMock(return_value=sample_query_result)
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('export_query_results', {
            'sql': 'SELECT * FROM employees',
            'format': 'csv'
        })
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'CSV Export' in result[0].text
        assert 'EMPLOYEE_ID,FIRST_NAME,LAST_NAME' in result[0].text

    @pytest.mark.unit
    async def test_call_tool_unknown_tool(self, oracle_mcp_server):
        """Test calling unknown tool"""
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler with unknown tool
        result = await handler('unknown_tool', {})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Error: Unknown tool' in result[0].text

    @pytest.mark.unit
    async def test_call_tool_exception_handling(self, oracle_mcp_server):
        """Test tool call exception handling"""
        # Mock the executor to raise an exception
        oracle_mcp_server.executor = MagicMock()
        oracle_mcp_server.executor.execute_query = AsyncMock(side_effect=Exception("Database error"))
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('execute_query', {'sql': 'SELECT * FROM employees'})
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert 'Error: Database error' in result[0].text

    @pytest.mark.unit
    async def test_run_missing_connection_string(self, oracle_mcp_server):
        """Test running server without connection string"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', None):
            with pytest.raises(SystemExit):
                await oracle_mcp_server.run()

    @pytest.mark.unit
    async def test_run_success(self, oracle_mcp_server):
        """Test successful server run"""
        # Mock stdio_server and other dependencies
        with patch('oracle_mcp_server.server.stdio_server') as mock_stdio:
            mock_streams = MagicMock()
            mock_stdio.return_value.__aenter__.return_value = mock_streams
            mock_stdio.return_value.__aexit__.return_value = None
            
            oracle_mcp_server.server.run = AsyncMock()
            
            await oracle_mcp_server.run()
            
            oracle_mcp_server.connection_manager.initialize_pool.assert_called_once()
            oracle_mcp_server.server.run.assert_called_once()

    @pytest.mark.unit
    async def test_csv_export_with_special_characters(self, oracle_mcp_server):
        """Test CSV export with special characters"""
        # Mock query result with special characters
        query_result = {
            'columns': ['NAME', 'DESCRIPTION'],
            'rows': [
                ['John, Jr.', 'Has "quotes" in description'],
                ['Jane', 'Normal description'],
                ['Bob', None],
            ],
            'row_count': 3,
            'execution_time_seconds': 0.05,
            'query': 'SELECT * FROM employees'
        }
        
        oracle_mcp_server.executor = MagicMock()
        oracle_mcp_server.executor.execute_query = AsyncMock(return_value=query_result)
        
        # Set up the handler
        await oracle_mcp_server.setup_handlers()
        
        # Get the handler function
        handler = oracle_mcp_server.server.call_tool.call_args[0][0]
        
        # Call the handler
        result = await handler('export_query_results', {
            'sql': 'SELECT * FROM employees',
            'format': 'csv'
        })
        
        assert len(result) == 1
        csv_content = result[0].text
        
        # Check that special characters are properly escaped
        assert '"John, Jr."' in csv_content
        assert '"Has ""quotes"" in description"' in csv_content
        assert ',,' in csv_content  # None value should be empty