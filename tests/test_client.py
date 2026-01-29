"""
Tests for Jenkins API Client
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from jenkins_mcp_server.client import JenkinsClient


class TestJenkinsClient:
    """Tests for JenkinsClient class."""
    
    @pytest.fixture
    def client(self):
        """Create a JenkinsClient instance for testing."""
        return JenkinsClient(
            url="https://jenkins.example.com",
            username="testuser",
            token="testtoken",
            verify_ssl=False
        )
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        mock = Mock()
        mock.status_code = 200
        mock.raise_for_status = Mock()
        return mock
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.url == "https://jenkins.example.com"
        assert client.username == "testuser"
        assert client.token == "testtoken"
        assert client.verify_ssl is False
    
    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL."""
        client = JenkinsClient(
            url="https://jenkins.example.com/",
            username="user",
            token="token"
        )
        assert client.url == "https://jenkins.example.com"
    
    @patch('jenkins_mcp_server.client.requests.Session')
    def test_list_jobs(self, mock_session_class, client, mock_response):
        """Test list_jobs method."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        mock_response.json.return_value = {
            'jobs': [
                {'name': 'job1', 'color': 'blue'},
                {'name': 'job2', 'color': 'red'}
            ]
        }
        client.session.request = Mock(return_value=mock_response)
        
        jobs = client.list_jobs()
        
        assert len(jobs) == 2
        assert jobs[0]['name'] == 'job1'
        assert jobs[1]['name'] == 'job2'
    
    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_job_details(self, mock_session_class, client, mock_response):
        """Test get_job_details method."""
        mock_response.json.return_value = {
            'name': 'test-job',
            'url': 'https://jenkins.example.com/job/test-job/',
            'buildable': True
        }
        client.session.request = Mock(return_value=mock_response)
        
        job = client.get_job_details('test-job')
        
        assert job['name'] == 'test-job'
        assert job['buildable'] is True
    
    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_build_info(self, mock_session_class, client, mock_response):
        """Test get_build_info method."""
        mock_response.json.return_value = {
            'number': 123,
            'result': 'SUCCESS',
            'duration': 60000
        }
        client.session.request = Mock(return_value=mock_response)
        
        build = client.get_build_info('test-job', 123)
        
        assert build['number'] == 123
        assert build['result'] == 'SUCCESS'
    
    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_build_console(self, mock_session_class, client, mock_response):
        """Test get_build_console method."""
        mock_response.text = "Build started\nStep 1\nStep 2\nBuild finished"
        client.session.request = Mock(return_value=mock_response)
        
        console = client.get_build_console('test-job', 123)
        
        assert "Build started" in console
        assert "Build finished" in console
    
    @patch('jenkins_mcp_server.client.requests.Session')
    def test_trigger_build(self, mock_session_class, client, mock_response):
        """Test trigger_build method."""
        mock_response.headers = {'Location': 'https://jenkins.example.com/queue/item/456/'}
        client.session.request = Mock(return_value=mock_response)
        
        result = client.trigger_build('test-job')
        
        assert result['queued'] is True
        assert '456' in result['queue_url']
    
    @patch('jenkins_mcp_server.client.requests.Session')
    def test_trigger_build_with_parameters(self, mock_session_class, client, mock_response):
        """Test trigger_build with parameters."""
        mock_response.headers = {'Location': 'https://jenkins.example.com/queue/item/456/'}
        client.session.request = Mock(return_value=mock_response)
        
        result = client.trigger_build('test-job', {'BRANCH': 'main'})
        
        assert result['queued'] is True
    
    def test_encode_job_path_simple(self, client):
        """Test _encode_job_path with simple job name."""
        result = client._encode_job_path('simple-job')
        assert result == 'simple-job'
    
    def test_encode_job_path_with_folder(self, client):
        """Test _encode_job_path with folder path."""
        result = client._encode_job_path('folder/subfolder/job')
        assert result == 'folder/job/subfolder/job/job'
    
    def test_encode_job_path_special_characters(self, client):
        """Test _encode_job_path with special characters."""
        result = client._encode_job_path('job with spaces')
        assert 'job%20with%20spaces' in result


class TestJenkinsClientIntegration:
    """Integration tests (require actual Jenkins server)."""
    
    @pytest.mark.skip(reason="Requires actual Jenkins server")
    def test_real_connection(self):
        """Test connection to real Jenkins server."""
        import os
        client = JenkinsClient(
            url=os.environ.get('JENKINS_URL', ''),
            username=os.environ.get('JENKINS_USERNAME', ''),
            token=os.environ.get('JENKINS_TOKEN', ''),
            verify_ssl=False
        )
        assert client.test_connection() is True
