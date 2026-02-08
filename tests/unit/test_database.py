"""
Unit tests for core/database.py module.

Tests database engine creation, session management, and dependency functions.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

# Set up test environment variables before importing database module
os.environ.setdefault('POSTGRES_USER', 'test_user')
os.environ.setdefault('POSTGRES_PASSWORD', 'test_password')
os.environ.setdefault('POSTGRES_DB', 'test_db')
os.environ.setdefault('VECTOR_POSTGRES_DB', 'test_vector_db')
os.environ.setdefault('S3_ENDPOINT', 'https://test.s3.com')
os.environ.setdefault('S3_ACCESS_KEY', 'test_access_key')
os.environ.setdefault('S3_SECRET_KEY', 'test_secret_key')
os.environ.setdefault('S3_BUCKET', 'test_bucket')

from core.database import (
    main_engine,
    vector_engine,
    MainSessionLocal,
    VectorSessionLocal,
    Base,
    get_main_db,
    get_vector_db
)


class TestDatabaseEngines:
    """Test database engine creation and configuration."""
    
    def test_main_engine_exists(self):
        """Test that main database engine is created."""
        assert main_engine is not None
        assert hasattr(main_engine, 'url')
    
    def test_vector_engine_exists(self):
        """Test that vector database engine is created."""
        assert vector_engine is not None
        assert hasattr(vector_engine, 'url')
    
    def test_main_engine_pool_configuration(self):
        """Test that main engine has correct pool configuration."""
        # Check pool_pre_ping is enabled
        assert main_engine.pool._pre_ping is True
        # Check pool size
        assert main_engine.pool.size() == 10
    
    def test_vector_engine_pool_configuration(self):
        """Test that vector engine has correct pool configuration."""
        # Check pool_pre_ping is enabled
        assert vector_engine.pool._pre_ping is True
        # Check pool size
        assert vector_engine.pool.size() == 10
    
    def test_main_engine_url_format(self):
        """Test that main engine URL has correct format."""
        url_str = str(main_engine.url)
        assert url_str.startswith('postgresql://')
        assert 'db_main' in url_str or 'localhost' in url_str
    
    def test_vector_engine_url_format(self):
        """Test that vector engine URL has correct format."""
        url_str = str(vector_engine.url)
        assert url_str.startswith('postgresql://')
        assert 'db_vector' in url_str or 'localhost' in url_str


class TestSessionLocals:
    """Test SessionLocal factory creation."""
    
    def test_main_session_local_exists(self):
        """Test that MainSessionLocal is created."""
        assert MainSessionLocal is not None
    
    def test_vector_session_local_exists(self):
        """Test that VectorSessionLocal is created."""
        assert VectorSessionLocal is not None
    
    def test_main_session_local_configuration(self):
        """Test that MainSessionLocal has correct configuration."""
        # Check autocommit and autoflush are disabled
        assert MainSessionLocal.kw.get('autocommit') is False
        assert MainSessionLocal.kw.get('autoflush') is False
    
    def test_vector_session_local_configuration(self):
        """Test that VectorSessionLocal has correct configuration."""
        # Check autocommit and autoflush are disabled
        assert VectorSessionLocal.kw.get('autocommit') is False
        assert VectorSessionLocal.kw.get('autoflush') is False


class TestBaseClass:
    """Test Base declarative class."""
    
    def test_base_exists(self):
        """Test that Base class is created."""
        assert Base is not None
    
    def test_base_has_metadata(self):
        """Test that Base has metadata attribute."""
        assert hasattr(Base, 'metadata')
    
    def test_base_has_registry(self):
        """Test that Base has registry attribute."""
        assert hasattr(Base, 'registry')


class TestDependencyFunctions:
    """Test dependency injection functions for FastAPI."""
    
    @patch('core.database.MainSessionLocal')
    def test_get_main_db_yields_session(self, mock_session_local):
        """Test that get_main_db yields a database session."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Execute generator
        gen = get_main_db()
        session = next(gen)
        
        # Verify session was created
        mock_session_local.assert_called_once()
        assert session == mock_session
    
    @patch('core.database.MainSessionLocal')
    def test_get_main_db_closes_session(self, mock_session_local):
        """Test that get_main_db closes session after use."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Execute generator and close it
        gen = get_main_db()
        next(gen)
        
        try:
            next(gen)
        except StopIteration:
            pass
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('core.database.VectorSessionLocal')
    def test_get_vector_db_yields_session(self, mock_session_local):
        """Test that get_vector_db yields a database session."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Execute generator
        gen = get_vector_db()
        session = next(gen)
        
        # Verify session was created
        mock_session_local.assert_called_once()
        assert session == mock_session
    
    @patch('core.database.VectorSessionLocal')
    def test_get_vector_db_closes_session(self, mock_session_local):
        """Test that get_vector_db closes session after use."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Execute generator and close it
        gen = get_vector_db()
        next(gen)
        
        try:
            next(gen)
        except StopIteration:
            pass
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('core.database.MainSessionLocal')
    def test_get_main_db_closes_on_exception(self, mock_session_local):
        """Test that get_main_db closes session even if exception occurs."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Execute generator and simulate exception
        gen = get_main_db()
        next(gen)
        
        try:
            gen.throw(Exception("Test exception"))
        except Exception:
            pass
        
        # Verify session was closed despite exception
        mock_session.close.assert_called_once()
    
    @patch('core.database.VectorSessionLocal')
    def test_get_vector_db_closes_on_exception(self, mock_session_local):
        """Test that get_vector_db closes session even if exception occurs."""
        # Setup mock
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # Execute generator and simulate exception
        gen = get_vector_db()
        next(gen)
        
        try:
            gen.throw(Exception("Test exception"))
        except Exception:
            pass
        
        # Verify session was closed despite exception
        mock_session.close.assert_called_once()
