import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
import oracledb

from oracle_mcp_server.server import (
    OracleConnection,
    DatabaseInspector,
    QueryExecutor,
    OracleMCPServer,
)


class TestIntegration:
    """Integration tests for Oracle MCP Server components"""

    @pytest.fixture
    def real_connection_string(self):
        """Get real connection string from environment or skip test"""
        connection_string = os.getenv('TEST_DB_CONNECTION_STRING')
        if not connection_string:
            pytest.skip("TEST_DB_CONNECTION_STRING environment variable not set")
        return connection_string

    @pytest.mark.integration
    async def test_oracle_connection_integration(self, real_connection_string):
        """Test actual Oracle connection (requires real database)"""
        oracle_conn = OracleConnection(real_connection_string)
        
        try:
            await oracle_conn.initialize_pool()
            connection = await oracle_conn.get_connection()
            
            # Test basic connection
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            result = cursor.fetchone()
            assert result[0] == 1
            
            connection.close()
            
        finally:
            oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_database_inspector_integration(self, real_connection_string):
        """Test database inspector with real database"""
        oracle_conn = OracleConnection(real_connection_string)
        inspector = DatabaseInspector(oracle_conn)
        
        try:
            await oracle_conn.initialize_pool()
            
            # Test getting tables
            tables = await inspector.get_tables()
            assert isinstance(tables, list)
            
            if tables:
                # Test getting columns for first table
                first_table = tables[0]
                columns = await inspector.get_table_columns(
                    first_table['table_name'], 
                    first_table['owner']
                )
                assert isinstance(columns, list)
                assert len(columns) > 0
                
                # Verify column structure
                for column in columns:
                    assert 'column_name' in column
                    assert 'data_type' in column
                    assert 'nullable' in column
            
            # Test getting views
            views = await inspector.get_views()
            assert isinstance(views, list)
            
            # Test getting procedures
            procedures = await inspector.get_procedures()
            assert isinstance(procedures, list)
            
        finally:
            oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_query_executor_integration(self, real_connection_string):
        """Test query executor with real database"""
        oracle_conn = OracleConnection(real_connection_string)
        executor = QueryExecutor(oracle_conn)
        
        try:
            await oracle_conn.initialize_pool()
            
            # Test simple query
            result = await executor.execute_query("SELECT 1 as test_col FROM DUAL")
            assert result['columns'] == ['TEST_COL']
            assert result['rows'] == [[1]]
            assert result['row_count'] == 1
            assert 'execution_time_seconds' in result
            
            # Test DESCRIBE query
            result = await executor.execute_query("DESCRIBE DUAL")
            assert 'columns' in result
            assert 'rows' in result
            
            # Test query with ROWNUM limit
            result = await executor.execute_query(
                "SELECT level FROM DUAL CONNECT BY level <= 200"
            )
            assert result['row_count'] <= 100  # Should be limited by QUERY_LIMIT_SIZE
            
            # Test explain query
            explain_result = await executor.explain_query("SELECT * FROM DUAL")
            assert 'execution_plan' in explain_result
            assert 'statement_id' in explain_result
            assert len(explain_result['execution_plan']) > 0
            
        finally:
            oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_dangerous_query_rejection(self, real_connection_string):
        """Test that dangerous queries are rejected"""
        oracle_conn = OracleConnection(real_connection_string)
        executor = QueryExecutor(oracle_conn)
        
        try:
            await oracle_conn.initialize_pool()
            
            dangerous_queries = [
                "DROP TABLE test_table",
                "DELETE FROM dual",
                "UPDATE dual SET dummy = 'X'",
                "INSERT INTO dual VALUES ('Y')",
                "TRUNCATE TABLE dual",
                "ALTER TABLE dual ADD COLUMN test VARCHAR2(100)",
                "CREATE TABLE test (id NUMBER)",
            ]
            
            for query in dangerous_queries:
                with pytest.raises(ValueError, match="Only SELECT, DESCRIBE, and EXPLAIN PLAN statements are allowed"):
                    await executor.execute_query(query)
                    
        finally:
            oracle_conn.close_pool()

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_connection_pooling(self, real_connection_string):
        """Test connection pooling functionality"""
        oracle_conn = OracleConnection(real_connection_string)
        
        try:
            await oracle_conn.initialize_pool()
            
            # Test multiple concurrent connections
            async def test_connection():
                connection = await oracle_conn.get_connection()
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()
                connection.close()
                return result[0]
            
            # Run multiple connections concurrently
            tasks = [test_connection() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            assert all(result == 1 for result in results)
            
        finally:
            oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_full_mcp_server_integration(self, real_connection_string):
        """Test full MCP server integration"""
        with patch('oracle_mcp_server.server.DB_CONNECTION_STRING', real_connection_string):
            server = OracleMCPServer()
            
            try:
                await server.connection_manager.initialize_pool()
                await server.setup_handlers()
                
                # Test list_tables tool
                tables = await server.inspector.get_tables()
                assert isinstance(tables, list)
                
                # Test execute_query tool
                result = await server.executor.execute_query("SELECT 1 FROM DUAL")
                assert result['columns'] == ['1']
                assert result['rows'] == [[1]]
                
                # Test describe_table tool if tables exist
                if tables:
                    first_table = tables[0]
                    columns = await server.inspector.get_table_columns(
                        first_table['table_name'],
                        first_table['owner']
                    )
                    assert isinstance(columns, list)
                    assert len(columns) > 0
                
            finally:
                server.connection_manager.close_pool()

    @pytest.mark.integration
    async def test_environment_variable_configuration(self, real_connection_string):
        """Test configuration through environment variables"""
        test_env = {
            'DB_CONNECTION_STRING': real_connection_string,
            'QUERY_LIMIT_SIZE': '50',
            'TABLE_WHITE_LIST': 'DUAL',
            'DEBUG': 'True'
        }
        
        with patch.dict(os.environ, test_env):
            # Import after patching environment
            from oracle_mcp_server.server import QUERY_LIMIT_SIZE, TABLE_WHITE_LIST, DEBUG
            
            # Test that environment variables are loaded
            assert QUERY_LIMIT_SIZE == 50
            assert TABLE_WHITE_LIST == ['DUAL']
            assert DEBUG == True
            
            # Test with query executor
            oracle_conn = OracleConnection(real_connection_string)
            executor = QueryExecutor(oracle_conn)
            
            try:
                await oracle_conn.initialize_pool()
                
                # Test that custom limit is applied
                result = await executor.execute_query(
                    "SELECT level FROM DUAL CONNECT BY level <= 100"
                )
                
                # Should be limited by custom QUERY_LIMIT_SIZE
                assert result['row_count'] <= 50
                
            finally:
                oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_error_handling_integration(self, real_connection_string):
        """Test error handling in integration scenarios"""
        oracle_conn = OracleConnection(real_connection_string)
        
        try:
            await oracle_conn.initialize_pool()
            
            # Test invalid SQL
            executor = QueryExecutor(oracle_conn)
            with pytest.raises(Exception):  # Should be oracledb.Error in real scenario
                await executor.execute_query("SELECT * FROM nonexistent_table")
            
            # Test invalid table name in inspector
            inspector = DatabaseInspector(oracle_conn)
            columns = await inspector.get_table_columns("NONEXISTENT_TABLE")
            assert columns == []  # Should return empty list, not raise exception
            
        finally:
            oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_data_type_handling_integration(self, real_connection_string):
        """Test handling of various Oracle data types"""
        oracle_conn = OracleConnection(real_connection_string)
        executor = QueryExecutor(oracle_conn)
        
        try:
            await oracle_conn.initialize_pool()
            
            # Test various data types
            test_queries = [
                "SELECT 123 as number_col FROM DUAL",
                "SELECT 'test string' as varchar_col FROM DUAL",
                "SELECT SYSDATE as date_col FROM DUAL",
                "SELECT NULL as null_col FROM DUAL",
                "SELECT 123.45 as decimal_col FROM DUAL",
            ]
            
            for query in test_queries:
                result = await executor.execute_query(query)
                assert result['row_count'] == 1
                assert len(result['columns']) == 1
                assert len(result['rows']) == 1
                
                # Check that data is JSON serializable
                import json
                json.dumps(result, default=str)
                
        finally:
            oracle_conn.close_pool()

    @pytest.mark.integration
    async def test_concurrent_operations(self, real_connection_string):
        """Test concurrent database operations"""
        oracle_conn = OracleConnection(real_connection_string)
        executor = QueryExecutor(oracle_conn)
        inspector = DatabaseInspector(oracle_conn)
        
        try:
            await oracle_conn.initialize_pool()
            
            # Run multiple operations concurrently
            tasks = [
                executor.execute_query("SELECT 1 FROM DUAL"),
                executor.execute_query("SELECT 2 FROM DUAL"),
                inspector.get_tables(),
                inspector.get_views(),
                executor.execute_query("SELECT SYSDATE FROM DUAL"),
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert results[0]['rows'][0][0] == 1
            assert results[1]['rows'][0][0] == 2
            assert isinstance(results[2], list)  # tables
            assert isinstance(results[3], list)  # views
            assert len(results[4]['rows']) == 1   # date query
            
        finally:
            oracle_conn.close_pool()