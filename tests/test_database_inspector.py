import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from oracle_mcp_server.server import DatabaseInspector


class TestDatabaseInspector:
    """Test cases for DatabaseInspector class"""

    @pytest.mark.unit
    def test_init(self, oracle_connection):
        """Test DatabaseInspector initialization"""
        inspector = DatabaseInspector(oracle_connection)
        
        assert inspector.connection_manager == oracle_connection

    @pytest.mark.unit
    async def test_get_tables_success(self, database_inspector, mock_connection, mock_cursor, sample_table_data):
        """Test successful table retrieval"""
        mock_cursor.fetchall.return_value = sample_table_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        tables = await database_inspector.get_tables()
        
        assert len(tables) == 3
        assert tables[0]['owner'] == 'HR'
        assert tables[0]['table_name'] == 'EMPLOYEES'
        assert tables[0]['num_rows'] == 100
        assert tables[0]['table_comment'] == 'Employee table'
        assert tables[0]['tablespace_name'] == 'USERS'
        
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    async def test_get_tables_with_owner_filter(self, database_inspector, mock_connection, mock_cursor, sample_table_data):
        """Test table retrieval with owner filter"""
        mock_cursor.fetchall.return_value = sample_table_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        tables = await database_inspector.get_tables(owner='HR')
        
        assert len(tables) == 3
        
        # Check that the query includes owner filter
        args, kwargs = mock_cursor.execute.call_args
        assert 'owner' in args[0].lower()
        assert 'HR' in args[1]

    @pytest.mark.unit
    @patch('oracle_mcp_server.server.TABLE_WHITE_LIST', ['EMPLOYEES', 'DEPARTMENTS'])
    async def test_get_tables_with_whitelist(self, database_inspector, mock_connection, mock_cursor, sample_table_data):
        """Test table retrieval with table whitelist"""
        mock_cursor.fetchall.return_value = sample_table_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        tables = await database_inspector.get_tables()
        
        assert len(tables) == 3
        
        # Check that the query includes whitelist filter
        args, kwargs = mock_cursor.execute.call_args
        assert 'table_0' in args[0]
        assert 'table_1' in args[0]
        assert 'EMPLOYEES' in args[1]
        assert 'DEPARTMENTS' in args[1]

    @pytest.mark.unit
    async def test_get_tables_with_date_handling(self, database_inspector, mock_connection, mock_cursor):
        """Test table retrieval with date handling"""
        test_date = datetime(2023, 1, 1, 10, 30, 45)
        table_data = [
            ("HR", "EMPLOYEES", 100, test_date, "Employee table", "USERS"),
        ]
        
        mock_cursor.fetchall.return_value = table_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        tables = await database_inspector.get_tables()
        
        assert len(tables) == 1
        assert tables[0]['last_analyzed'] == test_date.isoformat()

    @pytest.mark.unit
    async def test_get_table_columns_success(self, database_inspector, mock_connection, mock_cursor, sample_column_data):
        """Test successful column retrieval"""
        mock_cursor.fetchall.return_value = sample_column_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        columns = await database_inspector.get_table_columns('EMPLOYEES')
        
        assert len(columns) == 5
        assert columns[0]['column_name'] == 'EMPLOYEE_ID'
        assert columns[0]['data_type'] == 'NUMBER'
        assert columns[0]['nullable'] == 'N'
        assert columns[0]['column_comment'] == 'Employee ID'
        
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    async def test_get_table_columns_with_owner(self, database_inspector, mock_connection, mock_cursor, sample_column_data):
        """Test column retrieval with owner filter"""
        mock_cursor.fetchall.return_value = sample_column_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        columns = await database_inspector.get_table_columns('EMPLOYEES', owner='HR')
        
        assert len(columns) == 5
        
        # Check that the query includes owner filter
        args, kwargs = mock_cursor.execute.call_args
        assert 'owner' in args[0].lower()
        assert 'HR' in args[1]

    @pytest.mark.unit
    @patch('oracle_mcp_server.server.COLUMN_WHITE_LIST', ['EMPLOYEES.EMPLOYEE_ID', 'EMPLOYEES.FIRST_NAME'])
    async def test_get_table_columns_with_whitelist(self, database_inspector, mock_connection, mock_cursor, sample_column_data):
        """Test column retrieval with column whitelist"""
        mock_cursor.fetchall.return_value = sample_column_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        columns = await database_inspector.get_table_columns('EMPLOYEES')
        
        # Should only return columns that are in the whitelist
        assert len(columns) == 2
        assert columns[0]['column_name'] == 'EMPLOYEE_ID'
        assert columns[1]['column_name'] == 'FIRST_NAME'

    @pytest.mark.unit
    async def test_get_views_success(self, database_inspector, mock_connection, mock_cursor, sample_view_data):
        """Test successful view retrieval"""
        mock_cursor.fetchall.return_value = sample_view_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        views = await database_inspector.get_views()
        
        assert len(views) == 2
        assert views[0]['owner'] == 'HR'
        assert views[0]['view_name'] == 'EMP_DETAILS_VIEW'
        assert views[0]['view_comment'] == 'Employee details view'
        
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    async def test_get_views_with_owner_filter(self, database_inspector, mock_connection, mock_cursor, sample_view_data):
        """Test view retrieval with owner filter"""
        mock_cursor.fetchall.return_value = sample_view_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        views = await database_inspector.get_views(owner='HR')
        
        assert len(views) == 2
        
        # Check that the query includes owner filter
        args, kwargs = mock_cursor.execute.call_args
        assert 'owner' in args[0].lower()
        assert 'HR' in args[1]

    @pytest.mark.unit
    async def test_get_procedures_success(self, database_inspector, mock_connection, mock_cursor, sample_procedure_data):
        """Test successful procedure retrieval"""
        mock_cursor.fetchall.return_value = sample_procedure_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        procedures = await database_inspector.get_procedures()
        
        assert len(procedures) == 3
        assert procedures[0]['owner'] == 'HR'
        assert procedures[0]['object_name'] == 'ADD_EMPLOYEE'
        assert procedures[0]['object_type'] == 'PROCEDURE'
        assert procedures[0]['status'] == 'VALID'
        
        mock_cursor.execute.assert_called_once()
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    async def test_get_procedures_with_owner_filter(self, database_inspector, mock_connection, mock_cursor, sample_procedure_data):
        """Test procedure retrieval with owner filter"""
        mock_cursor.fetchall.return_value = sample_procedure_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        procedures = await database_inspector.get_procedures(owner='HR')
        
        assert len(procedures) == 3
        
        # Check that the query includes owner filter
        args, kwargs = mock_cursor.execute.call_args
        assert 'owner' in args[0].lower()
        assert 'HR' in args[1]

    @pytest.mark.unit
    async def test_get_procedures_with_date_handling(self, database_inspector, mock_connection, mock_cursor):
        """Test procedure retrieval with date handling"""
        test_date = datetime(2023, 1, 1, 10, 30, 45)
        procedure_data = [
            ("HR", "ADD_EMPLOYEE", "PROCEDURE", "VALID", test_date, test_date),
        ]
        
        mock_cursor.fetchall.return_value = procedure_data
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        procedures = await database_inspector.get_procedures()
        
        assert len(procedures) == 1
        assert procedures[0]['created'] == test_date.isoformat()
        assert procedures[0]['last_ddl_time'] == test_date.isoformat()

    @pytest.mark.unit
    async def test_connection_cleanup_on_exception(self, database_inspector, mock_connection, mock_cursor):
        """Test that connection is properly closed even when exception occurs"""
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        with pytest.raises(Exception):
            await database_inspector.get_tables()
        
        mock_connection.close.assert_called_once()

    @pytest.mark.unit
    async def test_empty_results_handling(self, database_inspector, mock_connection, mock_cursor):
        """Test handling of empty results"""
        mock_cursor.fetchall.return_value = []
        mock_connection.cursor.return_value = mock_cursor
        database_inspector.connection_manager.get_connection = AsyncMock(return_value=mock_connection)
        
        tables = await database_inspector.get_tables()
        views = await database_inspector.get_views()
        procedures = await database_inspector.get_procedures()
        columns = await database_inspector.get_table_columns('NONEXISTENT_TABLE')
        
        assert tables == []
        assert views == []
        assert procedures == []
        assert columns == []