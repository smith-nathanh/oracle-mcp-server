import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import oracledb

from oracle_mcp_server.server import OracleConnection


class TestOracleConnection:
    """Test cases for OracleConnection class"""

    @pytest.mark.unit
    def test_init_with_connection_string(self):
        """Test initialization with connection string"""
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        assert oracle_conn.connection_string == connection_string
        assert oracle_conn.pool is None

    @pytest.mark.unit
    def test_init_with_empty_connection_string(self):
        """Test initialization with empty connection string"""
        oracle_conn = OracleConnection("")
        
        assert oracle_conn.connection_string == ""
        assert oracle_conn.pool is None

    @pytest.mark.unit
    @patch('oracledb.create_pool')
    @pytest.mark.asyncio
    async def test_initialize_pool_success(self, mock_create_pool):
        """Test successful pool initialization"""
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool
        
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        await oracle_conn.initialize_pool()
        
        assert oracle_conn.pool == mock_pool
        mock_create_pool.assert_called_once_with(
            dsn="localhost:1521/testdb",
            user="testuser",
            password="testpass",
            min=1,
            max=10,
            increment=1,
            getmode=oracledb.POOL_GETMODE_WAIT,
        )

    @pytest.mark.unit
    @patch('oracledb.create_pool')
    @pytest.mark.asyncio
    async def test_initialize_pool_no_credentials(self, mock_create_pool):
        """Test pool initialization without user/password"""
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool
        
        connection_string = "localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        await oracle_conn.initialize_pool()
        
        assert oracle_conn.pool == mock_pool
        mock_create_pool.assert_called_once_with(
            dsn="localhost:1521/testdb",
            min=1,
            max=10,
            increment=1,
            getmode=oracledb.POOL_GETMODE_WAIT,
        )

    @pytest.mark.unit
    @patch('oracledb.create_pool')
    @pytest.mark.asyncio
    async def test_initialize_pool_no_at_symbol(self, mock_create_pool):
        """Test pool initialization with connection string without @ symbol"""
        mock_pool = MagicMock()
        mock_create_pool.return_value = mock_pool
        
        connection_string = "localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        await oracle_conn.initialize_pool()
        
        assert oracle_conn.pool == mock_pool
        mock_create_pool.assert_called_once_with(
            dsn="localhost:1521/testdb",
            min=1,
            max=10,
            increment=1,
            getmode=oracledb.POOL_GETMODE_WAIT,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_pool_empty_connection_string(self):
        """Test pool initialization with empty connection string"""
        oracle_conn = OracleConnection("")
        
        with pytest.raises(ValueError, match="Database connection string is required"):
            await oracle_conn.initialize_pool()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_pool_none_connection_string(self):
        """Test pool initialization with None connection string"""
        oracle_conn = OracleConnection(None)
        
        with pytest.raises(ValueError, match="Database connection string is required"):
            await oracle_conn.initialize_pool()

    @pytest.mark.unit
    @patch('oracledb.create_pool')
    @pytest.mark.asyncio
    async def test_initialize_pool_oracledb_exception(self, mock_create_pool):
        """Test pool initialization with oracledb exception"""
        mock_create_pool.side_effect = oracledb.Error("Database connection failed")
        
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        with pytest.raises(oracledb.Error):
            await oracle_conn.initialize_pool()

    @pytest.mark.unit
    @patch('oracledb.create_pool')
    @pytest.mark.asyncio
    async def test_get_connection_pool_exists(self, mock_create_pool):
        """Test getting connection when pool already exists"""
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.acquire.return_value = mock_connection
        mock_create_pool.return_value = mock_pool
        
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        # Initialize pool first
        await oracle_conn.initialize_pool()
        
        # Get connection
        connection = await oracle_conn.get_connection()
        
        assert connection == mock_connection
        mock_pool.acquire.assert_called_once()

    @pytest.mark.unit
    @patch('oracledb.create_pool')
    @pytest.mark.asyncio
    async def test_get_connection_pool_not_exists(self, mock_create_pool):
        """Test getting connection when pool doesn't exist"""
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_pool.acquire.return_value = mock_connection
        mock_create_pool.return_value = mock_pool
        
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        # Get connection without initializing pool first
        connection = await oracle_conn.get_connection()
        
        assert connection == mock_connection
        assert oracle_conn.pool == mock_pool
        mock_pool.acquire.assert_called_once()

    @pytest.mark.unit
    def test_close_pool_with_pool(self):
        """Test closing pool when it exists"""
        mock_pool = MagicMock()
        
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        oracle_conn.pool = mock_pool
        
        oracle_conn.close_pool()
        
        mock_pool.close.assert_called_once()

    @pytest.mark.unit
    def test_close_pool_without_pool(self):
        """Test closing pool when it doesn't exist"""
        connection_string = "testuser/testpass@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        # Should not raise an exception
        oracle_conn.close_pool()

    @pytest.mark.unit
    def test_connection_string_parsing_edge_cases(self):
        """Test various edge cases in connection string parsing"""
        
        # Test with no slash in user_pass
        connection_string = "testuser@localhost:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        assert oracle_conn.connection_string == connection_string
        
        # Test with multiple @ symbols (should split on first one)
        connection_string = "user@domain/pass@host:1521/testdb"
        oracle_conn = OracleConnection(connection_string)
        
        assert oracle_conn.connection_string == connection_string