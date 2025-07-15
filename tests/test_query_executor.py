import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from oracle_mcp_server.server import QueryExecutor


class TestQueryExecutor:
    """Test cases for QueryExecutor class"""

    @pytest.mark.unit
    def test_init(self, oracle_connection):
        """Test QueryExecutor initialization"""
        executor = QueryExecutor(oracle_connection)
        
        assert executor.connection_manager == oracle_connection

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_select_success(self, query_executor, mock_connection, mock_cursor):
        """Test successful SELECT query execution"""
        mock_cursor.description = [('EMPLOYEE_ID',), ('FIRST_NAME',), ('LAST_NAME',)]
        mock_cursor.fetchall.return_value = [
            (1, 'John', 'Doe'),
            (2, 'Jane', 'Smith'),
        ]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT employee_id, first_name, last_name FROM employees"
        result = await query_executor.execute_query(sql)
        
        assert result['columns'] == ['EMPLOYEE_ID', 'FIRST_NAME', 'LAST_NAME']
        assert result['rows'] == [[1, 'John', 'Doe'], [2, 'Jane', 'Smith']]
        assert result['row_count'] == 2
        assert 'execution_time_seconds' in result
        assert 'ROWNUM' in result['query']
        
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_with_parameters(self, query_executor, mock_connection, mock_cursor):
        """Test query execution with parameters"""
        mock_cursor.description = [('COUNT(*)',)]
        mock_cursor.fetchall.return_value = [(5,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT COUNT(*) FROM employees WHERE department_id = :dept_id"
        params = [10]
        result = await query_executor.execute_query(sql, params)
        
        assert result['columns'] == ['COUNT(*)']
        assert result['rows'] == [[5]]
        assert result['row_count'] == 1
        
        expected_sql = sql + " AND ROWNUM <= 100"  # Code automatically adds ROWNUM limit
        mock_cursor.execute.assert_called_once_with(expected_sql, params)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_describe_statement(self, query_executor, mock_connection, mock_cursor):
        """Test DESCRIBE statement execution"""
        mock_cursor.description = [('COLUMN_NAME',), ('DATA_TYPE',)]
        mock_cursor.fetchall.return_value = [
            ('EMPLOYEE_ID', 'NUMBER'),
            ('FIRST_NAME', 'VARCHAR2'),
        ]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "DESCRIBE employees"
        result = await query_executor.execute_query(sql)
        
        assert result['columns'] == ['COLUMN_NAME', 'DATA_TYPE']
        assert result['rows'] == [['EMPLOYEE_ID', 'NUMBER'], ['FIRST_NAME', 'VARCHAR2']]
        assert result['row_count'] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_explain_plan(self, query_executor, mock_connection, mock_cursor):
        """Test EXPLAIN PLAN statement execution"""
        mock_cursor.description = None
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "EXPLAIN PLAN FOR SELECT * FROM employees"
        result = await query_executor.execute_query(sql)
        
        assert result['message'] == 'Query executed successfully'
        assert 'execution_time_seconds' in result
        expected_sql = "EXPLAIN PLAN FOR SELECT * FROM employees WHERE ROWNUM <= 100"  # Code adds ROWNUM even to EXPLAIN
        assert result['query'] == expected_sql

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_dangerous_keywords(self, query_executor):
        """Test rejection of dangerous SQL keywords"""
        dangerous_queries = [
            "DROP TABLE employees",
            "DELETE FROM employees",
            "TRUNCATE TABLE employees",
            "ALTER TABLE employees ADD COLUMN test VARCHAR2(100)",
            "CREATE TABLE test (id NUMBER)",
            "INSERT INTO employees VALUES (1, 'Test')",
            "UPDATE employees SET first_name = 'Test'",
        ]
        
        for sql in dangerous_queries:
            with pytest.raises(ValueError, match="Only SELECT, DESCRIBE, and EXPLAIN PLAN statements are allowed"):
                await query_executor.execute_query(sql)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_with_statement(self, query_executor, mock_connection, mock_cursor):
        """Test WITH statement execution"""
        mock_cursor.description = [('EMPLOYEE_ID',), ('FIRST_NAME',)]
        mock_cursor.fetchall.return_value = [(1, 'John'), (2, 'Jane')]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "WITH dept_employees AS (SELECT * FROM employees WHERE department_id = 10) SELECT employee_id, first_name FROM dept_employees"
        result = await query_executor.execute_query(sql)
        
        assert result['columns'] == ['EMPLOYEE_ID', 'FIRST_NAME']
        assert result['rows'] == [[1, 'John'], [2, 'Jane']]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_rownum_limit_addition(self, query_executor, mock_connection, mock_cursor):
        """Test automatic ROWNUM limit addition"""
        mock_cursor.description = [('EMPLOYEE_ID',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        # Test simple SELECT without WHERE clause
        sql = "SELECT employee_id FROM employees"
        result = await query_executor.execute_query(sql)
        
        args, kwargs = mock_cursor.execute.call_args
        assert "ROWNUM <= 100" in args[0]
        assert "WHERE ROWNUM <= 100" in args[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_rownum_limit_with_where(self, query_executor, mock_connection, mock_cursor):
        """Test ROWNUM limit addition with existing WHERE clause"""
        mock_cursor.description = [('EMPLOYEE_ID',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT employee_id FROM employees WHERE department_id = 10"
        result = await query_executor.execute_query(sql)
        
        args, kwargs = mock_cursor.execute.call_args
        assert "AND ROWNUM <= 100" in args[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_rownum_limit_with_order_by(self, query_executor, mock_connection, mock_cursor):
        """Test ROWNUM limit addition with ORDER BY clause"""
        mock_cursor.description = [('EMPLOYEE_ID',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT employee_id FROM employees ORDER BY employee_id"
        result = await query_executor.execute_query(sql)
        
        args, kwargs = mock_cursor.execute.call_args
        assert "SELECT * FROM (" in args[0]
        assert "WHERE ROWNUM <= 100" in args[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_existing_rownum(self, query_executor, mock_connection, mock_cursor):
        """Test that ROWNUM is not added when already present"""
        mock_cursor.description = [('EMPLOYEE_ID',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT employee_id FROM employees WHERE ROWNUM <= 50"
        result = await query_executor.execute_query(sql)
        
        args, kwargs = mock_cursor.execute.call_args
        assert args[0] == sql  # Should not be modified

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_lob_handling(self, query_executor, mock_connection, mock_cursor):
        """Test LOB (Large Object) handling"""
        mock_lob = MagicMock()
        mock_lob.read.return_value = "Large text content"
        
        mock_cursor.description = [('ID',), ('TEXT_CONTENT',)]
        mock_cursor.fetchall.return_value = [(1, mock_lob)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT id, text_content FROM documents"
        result = await query_executor.execute_query(sql)
        
        assert result['rows'] == [[1, 'Large text content']]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_datetime_handling(self, query_executor, mock_connection, mock_cursor):
        """Test datetime object handling"""
        test_date = datetime(2023, 1, 1, 10, 30, 45)
        
        mock_cursor.description = [('ID',), ('CREATED_DATE',)]
        mock_cursor.fetchall.return_value = [(1, test_date)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT id, created_date FROM employees"
        result = await query_executor.execute_query(sql)
        
        assert result['rows'] == [[1, test_date.isoformat()]]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_query_none_values(self, query_executor, mock_connection, mock_cursor):
        """Test handling of None values"""
        mock_cursor.description = [('ID',), ('OPTIONAL_FIELD',)]
        mock_cursor.fetchall.return_value = [(1, None)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT id, optional_field FROM employees"
        result = await query_executor.execute_query(sql)
        
        assert result['rows'] == [[1, None]]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_explain_query_success(self, query_executor, mock_connection, mock_cursor):
        """Test successful query explanation"""
        explain_data = [
            ('SELECT STATEMENT', None, 100, 1000, 50000),
            ('  TABLE ACCESS FULL', 'EMPLOYEES', 100, 1000, 50000),
        ]
        mock_cursor.__iter__ = lambda self: iter(explain_data)
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT * FROM employees"
        result = await query_executor.explain_query(sql)
        
        assert 'execution_plan' in result
        assert 'statement_id' in result
        assert len(result['execution_plan']) == 2
        assert result['execution_plan'][0]['operation'] == 'SELECT STATEMENT'
        assert result['execution_plan'][0]['cost'] == 100
        
        # Check that explain plan was executed
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 3  # EXPLAIN PLAN, SELECT from plan_table, DELETE from plan_table
        assert 'EXPLAIN PLAN' in calls[0][0][0]
        assert 'plan_table' in calls[1][0][0]
        assert 'DELETE FROM plan_table' in calls[2][0][0]
        
        mock_connection.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_explain_query_statement_id_unique(self, query_executor, mock_connection, mock_cursor):
        """Test that explain query generates unique statement IDs"""
        mock_cursor.__iter__ = lambda self: iter([])
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        # Mock datetime to return different times for unique statement IDs
        with patch('oracle_mcp_server.server.datetime') as mock_datetime:
            mock_datetime.now.side_effect = [
                datetime(2023, 1, 1, 10, 30, 45),  # First call
                datetime(2023, 1, 1, 10, 30, 46),  # Second call (different second)
            ]
            mock_datetime.strftime = datetime.strftime  # Keep strftime method
            
            sql = "SELECT * FROM employees"
            result1 = await query_executor.explain_query(sql)
            result2 = await query_executor.explain_query(sql)
            
            assert result1['statement_id'] != result2['statement_id']
        assert result1['statement_id'].startswith('MCP_EXPLAIN_')
        assert result2['statement_id'].startswith('MCP_EXPLAIN_')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_exception(self, query_executor, mock_connection, mock_cursor):
        """Test that connection is properly closed even when exception occurs"""
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        with pytest.raises(Exception):
            await query_executor.execute_query("SELECT * FROM employees")
        
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execution_time_measurement(self, query_executor, mock_connection, mock_cursor):
        """Test that execution time is measured"""
        mock_cursor.description = [('ID',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT id FROM employees"
        result = await query_executor.execute_query(sql)
        
        assert 'execution_time_seconds' in result
        assert isinstance(result['execution_time_seconds'], float)
        assert result['execution_time_seconds'] >= 0

    @pytest.mark.unit
    @patch('oracle_mcp_server.server.QUERY_LIMIT_SIZE', 50)
    @pytest.mark.asyncio
    async def test_custom_query_limit(self, query_executor, mock_connection, mock_cursor):
        """Test custom query limit configuration"""
        mock_cursor.description = [('ID',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connection.cursor.return_value = mock_cursor
        query_executor.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        sql = "SELECT id FROM employees"
        result = await query_executor.execute_query(sql)
        
        args, kwargs = mock_cursor.execute.call_args
        assert "ROWNUM <= 50" in args[0]