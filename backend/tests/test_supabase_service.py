"""
Tests for Supabase Service with mocked client.

These tests verify Supabase authentication and database functionality
without requiring actual Supabase credentials.
Run with: pytest tests/test_supabase_service.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestSupabaseConfig:
    """Tests for SupabaseConfig dataclass."""

    def test_default_config_values(self):
        """Should have empty default config values."""
        with patch.dict('os.environ', {}, clear=True):
            from services.supabase_service import SupabaseConfig
            config = SupabaseConfig.from_env()
            assert config.url == ''
            assert config.key == ''
            assert config.is_configured() is False

    def test_config_from_env(self):
        """Should load config from environment variables."""
        with patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test-key-123'
        }):
            from services.supabase_service import SupabaseConfig
            config = SupabaseConfig.from_env()
            assert config.url == 'https://test.supabase.co'
            assert config.key == 'test-key-123'
            assert config.is_configured() is True


class TestSupabaseServiceUnit:
    """Unit tests for SupabaseService with mocked client."""

    @pytest.fixture
    def mock_supabase(self):
        """Create mocked Supabase client."""
        with patch('services.supabase_service.create_client') as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client
            yield mock_client

    def test_init_creates_client(self, mock_supabase):
        """Should create Supabase client when configured."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        config = SupabaseConfig(
            url='https://test.supabase.co',
            key='test-key-123'
        )
        service = SupabaseService(config=config)
        
        assert service.is_available() is True

    def test_is_available_false_when_not_configured(self):
        """Should return False when not configured."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        config = SupabaseConfig(url='', key='')
        service = SupabaseService(config=config)
        
        assert service.is_available() is False

    # =====================
    # Authentication Tests
    # =====================

    def test_sign_up_success(self, mock_supabase):
        """Should sign up user successfully."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        # Mock user and session
        mock_user = MagicMock()
        mock_user.id = 'user-123'
        mock_user.email = 'test@example.com'
        
        mock_session = MagicMock()
        mock_session.access_token = 'token-abc'
        
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session
        
        mock_supabase.auth.sign_up.return_value = mock_response
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        result = service.sign_up('test@example.com', 'password123')
        
        assert 'user' in result
        assert result['user']['email'] == 'test@example.com'
        assert 'session' in result

    def test_sign_in_success(self, mock_supabase):
        """Should sign in user successfully."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_user = MagicMock()
        mock_user.id = 'user-123'
        mock_user.email = 'test@example.com'
        
        mock_session = MagicMock()
        mock_session.access_token = 'token-abc'
        mock_session.refresh_token = 'refresh-xyz'
        mock_session.expires_at = 1234567890
        
        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session
        
        mock_supabase.auth.sign_in_with_password.return_value = mock_response
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        result = service.sign_in('test@example.com', 'password123')
        
        assert 'user' in result
        assert result['user']['email'] == 'test@example.com'
        assert result['session']['access_token'] == 'token-abc'

    def test_sign_in_failure(self, mock_supabase):
        """Should return error on invalid credentials."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_supabase.auth.sign_in_with_password.side_effect = Exception('Invalid credentials')
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        result = service.sign_in('test@example.com', 'wrong-password')
        
        assert 'error' in result

    def test_sign_out_success(self, mock_supabase):
        """Should sign out successfully."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_supabase.auth.sign_out.return_value = None
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        result = service.sign_out()
        
        assert result == {'success': True}

    def test_get_user_success(self, mock_supabase):
        """Should get user from access token."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_user = MagicMock()
        mock_user.id = 'user-123'
        mock_user.email = 'test@example.com'
        
        mock_response = MagicMock()
        mock_response.user = mock_user
        
        mock_supabase.auth.get_user.return_value = mock_response
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        result = service.get_user('access-token-123')
        
        assert result is not None
        assert result['email'] == 'test@example.com'

    # =====================
    # Jobs Tests
    # =====================

    def test_get_jobs_success(self, mock_supabase):
        """Should get jobs from database."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_response = MagicMock()
        mock_response.data = [
            {'id': 'job-1', 'repo': 'owner/repo', 'status': 'completed'},
            {'id': 'job-2', 'repo': 'owner/repo', 'status': 'processing'},
        ]
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_supabase.table.return_value = mock_query
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        jobs = service.get_jobs()
        
        assert len(jobs) == 2
        assert jobs[0]['id'] == 'job-1'

    def test_save_job_success(self, mock_supabase):
        """Should save job to database."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_response = MagicMock()
        mock_response.data = [{'id': 'job-1', 'repo': 'owner/repo'}]
        
        mock_query = MagicMock()
        mock_query.upsert.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_supabase.table.return_value = mock_query
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        job = {
            'id': 'job-1',
            'repo': 'owner/repo',
            'issueNumber': 123,
            'status': 'processing',
        }
        
        result = service.save_job(job)
        
        assert result['id'] == 'job-1'

    def test_get_job_by_id_success(self, mock_supabase):
        """Should get single job by ID."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_response = MagicMock()
        mock_response.data = {'id': 'job-1', 'repo': 'owner/repo'}
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.single.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_supabase.table.return_value = mock_query
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        job = service.get_job_by_id('job-1')
        
        assert job is not None
        assert job['id'] == 'job-1'

    # =====================
    # Issues Tests
    # =====================

    def test_get_issues_count_success(self, mock_supabase):
        """Should get issues count."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        mock_response = MagicMock()
        mock_response.count = 42
        
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.execute.return_value = mock_response
        
        mock_supabase.table.return_value = mock_query
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        count = service.get_issues_count()
        
        assert count == 42

    def test_get_stats_success(self, mock_supabase):
        """Should get aggregated stats."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        # Mock jobs response
        mock_jobs_response = MagicMock()
        mock_jobs_response.data = [
            {'status': 'completed'},
            {'status': 'completed'},
            {'status': 'failed'},
            {'status': 'processing'},
        ]
        
        # Mock issues count response
        mock_issues_response = MagicMock()
        mock_issues_response.count = 10
        
        def mock_table(table_name):
            mock_query = MagicMock()
            if table_name == 'jobs':
                mock_query.select.return_value = mock_query
                mock_query.order.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.execute.return_value = mock_jobs_response
            else:  # issues
                mock_query.select.return_value = mock_query
                mock_query.execute.return_value = mock_issues_response
            return mock_query
        
        mock_supabase.table.side_effect = mock_table
        
        config = SupabaseConfig(url='https://test.supabase.co', key='test-key')
        service = SupabaseService(config=config)
        
        stats = service.get_stats()
        
        assert stats['total_jobs'] == 4
        assert stats['completed_jobs'] == 2
        assert stats['failed_jobs'] == 1
        assert stats['processing_jobs'] == 1


class TestSupabaseNotConfigured:
    """Tests for when Supabase is not configured."""

    def test_methods_return_gracefully(self):
        """Should return safe defaults when not configured."""
        from services.supabase_service import SupabaseService, SupabaseConfig
        
        config = SupabaseConfig(url='', key='')
        service = SupabaseService(config=config)
        
        assert service.sign_up('email', 'pass') == {'error': 'Supabase not configured'}
        assert service.sign_in('email', 'pass') == {'error': 'Supabase not configured'}
        assert service.sign_out() == {'error': 'Supabase not configured'}
        assert service.get_user('token') is None
        assert service.get_jobs() == []
        assert service.save_job({'id': 'test'}) == {'error': 'Supabase not configured'}
        assert service.get_job_by_id('test') is None
        assert service.get_issues_count() == 0
