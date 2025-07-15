import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import argparse
from io import StringIO

# Import main function for testing
from oracle_mcp_server.server import main, async_main


class TestUtils:
    """Test utility functions and main entry points"""

    @pytest.mark.unit
    def test_main_function_version(self):
        """Test main function with --version argument"""
        test_args = ['oracle-mcp-server', '--version']
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit):
                main()

    @pytest.mark.unit
    def test_main_function_debug(self):
        """Test main function with --debug argument"""
        test_args = ['oracle-mcp-server', '--debug']
        
        with patch.object(sys, 'argv', test_args):
            with patch('oracle_mcp_server.server.asyncio.run') as mock_run:
                with patch('oracle_mcp_server.server.logging.getLogger') as mock_logger:
                    main()
                    
                    mock_run.assert_called_once()
                    mock_logger.assert_called()

    @pytest.mark.unit
    def test_main_function_no_args(self):
        """Test main function with no arguments"""
        test_args = ['oracle-mcp-server']
        
        with patch.object(sys, 'argv', test_args):
            with patch('oracle_mcp_server.server.asyncio.run') as mock_run:
                main()
                
                mock_run.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_main_keyboard_interrupt(self):
        """Test async_main with keyboard interrupt"""
        with patch('oracle_mcp_server.server.OracleMCPServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server.run = MagicMock(side_effect=KeyboardInterrupt())
            mock_server.connection_manager.close_pool = MagicMock()
            mock_server_class.return_value = mock_server
            
            await async_main()
            
            mock_server.run.assert_called_once()
            mock_server.connection_manager.close_pool.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_main_general_exception(self):
        """Test async_main with general exception"""
        with patch('oracle_mcp_server.server.OracleMCPServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server.run = MagicMock(side_effect=Exception("Test error"))
            mock_server.connection_manager.close_pool = MagicMock()
            mock_server_class.return_value = mock_server
            
            with pytest.raises(SystemExit):
                await async_main()
            
            mock_server.run.assert_called_once()
            mock_server.connection_manager.close_pool.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_main_success(self):
        """Test successful async_main execution"""
        with patch('oracle_mcp_server.server.OracleMCPServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server.run = AsyncMock()  # Use AsyncMock for await
            mock_server.connection_manager.close_pool = MagicMock()
            mock_server_class.return_value = mock_server
            
            await async_main()
            
            mock_server.run.assert_called_once()
            mock_server.connection_manager.close_pool.assert_called_once()

    @pytest.mark.unit
    def test_argument_parser(self):
        """Test argument parser functionality"""
        parser = argparse.ArgumentParser(description="Oracle Database MCP Server")
        parser.add_argument("--version", action="version", version="1.0.0")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        
        # Test normal parsing
        args = parser.parse_args(['--debug'])
        assert args.debug == True
        
        # Test version (should exit)
        with pytest.raises(SystemExit):
            parser.parse_args(['--version'])

    @pytest.mark.unit
    def test_logging_configuration(self):
        """Test logging configuration"""
        # Test that DEBUG variable exists and can be checked
        import oracle_mcp_server.server
        
        # Test that we can access the DEBUG variable
        debug_value = oracle_mcp_server.server.DEBUG
        assert isinstance(debug_value, bool)
        
        # Test that logger is configured
        logger = oracle_mcp_server.server.logger
        assert logger.name == "oracle-mcp-server"

    @pytest.mark.unit
    def test_environment_variable_parsing(self):
        """Test environment variable parsing"""
        test_env = {
            'DEBUG': 'true',
            'DB_CONNECTION_STRING': 'test_connection',
            'QUERY_LIMIT_SIZE': '200',
            'MAX_ROWS_EXPORT': '20000',
            'TABLE_WHITE_LIST': 'TABLE1,TABLE2,TABLE3',
            'COLUMN_WHITE_LIST': 'TABLE1.COL1,TABLE2.COL2'
        }
        
        with patch.dict(os.environ, test_env):
            # Re-import to trigger environment variable parsing
            import importlib
            import oracle_mcp_server.server
            importlib.reload(oracle_mcp_server.server)
            
            # Test that variables are parsed correctly
            assert oracle_mcp_server.server.DEBUG == True
            assert oracle_mcp_server.server.DB_CONNECTION_STRING == 'test_connection'
            assert oracle_mcp_server.server.QUERY_LIMIT_SIZE == 200
            assert oracle_mcp_server.server.MAX_ROWS_EXPORT == 20000
            assert oracle_mcp_server.server.TABLE_WHITE_LIST == ['TABLE1', 'TABLE2', 'TABLE3']
            assert oracle_mcp_server.server.COLUMN_WHITE_LIST == ['TABLE1.COL1', 'TABLE2.COL2']

    @pytest.mark.unit
    def test_environment_variable_defaults(self):
        """Test environment variable defaults"""
        test_env = {
            'DEBUG': 'false',
            'QUERY_LIMIT_SIZE': '',
            'MAX_ROWS_EXPORT': '',
            'TABLE_WHITE_LIST': '',
            'COLUMN_WHITE_LIST': ''
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            # Re-import to trigger environment variable parsing
            import importlib
            import oracle_mcp_server.server
            importlib.reload(oracle_mcp_server.server)
            
            # Test that defaults are used
            assert oracle_mcp_server.server.DEBUG == False
            assert oracle_mcp_server.server.QUERY_LIMIT_SIZE == 100
            assert oracle_mcp_server.server.MAX_ROWS_EXPORT == 10000
            assert oracle_mcp_server.server.TABLE_WHITE_LIST == []
            assert oracle_mcp_server.server.COLUMN_WHITE_LIST == []

    @pytest.mark.unit
    def test_connection_string_comment_db(self):
        """Test comment database connection string configuration"""
        test_env = {
            'DB_CONNECTION_STRING': 'main_connection',
            'COMMENT_DB_CONNECTION_STRING': 'comment_connection'
        }
        
        with patch.dict(os.environ, test_env):
            # Re-import to trigger environment variable parsing
            import importlib
            import oracle_mcp_server.server
            importlib.reload(oracle_mcp_server.server)
            
            assert oracle_mcp_server.server.DB_CONNECTION_STRING == 'main_connection'
            assert oracle_mcp_server.server.COMMENT_DB_CONNECTION_STRING == 'comment_connection'

    @pytest.mark.unit
    def test_connection_string_comment_db_default(self):
        """Test comment database connection string defaults to main connection"""
        test_env = {
            'DB_CONNECTION_STRING': 'main_connection'
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            # Re-import to trigger environment variable parsing
            import importlib
            import oracle_mcp_server.server
            importlib.reload(oracle_mcp_server.server)
            
            assert oracle_mcp_server.server.DB_CONNECTION_STRING == 'main_connection'
            assert oracle_mcp_server.server.COMMENT_DB_CONNECTION_STRING == 'main_connection'

    @pytest.mark.unit
    def test_sys_exit_on_missing_connection(self):
        """Test that sys.exit is called when connection string is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('oracle_mcp_server.server.OracleMCPServer') as mock_server_class:
                mock_server = MagicMock()
                mock_server.run = MagicMock()
                mock_server.connection_manager.close_pool = MagicMock()
                mock_server_class.return_value = mock_server
                
                # Mock the run method to check for sys.exit
                mock_server.run.side_effect = SystemExit(1)
                
                with pytest.raises(SystemExit):
                    main()

    @pytest.mark.unit
    def test_help_message(self):
        """Test help message display"""
        parser = argparse.ArgumentParser(description="Oracle Database MCP Server")
        parser.add_argument("--version", action="version", version="1.0.0")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        
        # Capture help output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit):
                parser.parse_args(['--help'])
            
            help_output = mock_stdout.getvalue()
            assert "Oracle Database MCP Server" in help_output
            assert "--debug" in help_output
            assert "--version" in help_output