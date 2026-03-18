"""
Tests for Jenkins API Client
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from jenkins_mcp_server.client import (
    JenkinsClient,
    JOB_TEMPLATES,
    render_job_template,
)


# ---------------------------------------------------------------------------
# Client basics
# ---------------------------------------------------------------------------

class TestJenkinsClient:
    """Tests for JenkinsClient class."""

    @pytest.fixture
    def client(self):
        return JenkinsClient(
            url="https://jenkins.example.com",
            username="testuser",
            token="testtoken",
            verify_ssl=False,
        )

    @pytest.fixture
    def mock_response(self):
        mock = Mock()
        mock.status_code = 200
        mock.raise_for_status = Mock()
        return mock

    def test_init(self, client):
        assert client.url == "https://jenkins.example.com"
        assert client.username == "testuser"
        assert client.verify_ssl is False

    def test_url_trailing_slash_removed(self):
        c = JenkinsClient(url="https://jenkins.example.com/", username="u", token="t")
        assert c.url == "https://jenkins.example.com"

    # --- Original methods ------------------------------------------------

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_list_jobs(self, mock_session_class, client, mock_response):
        mock_response.json.return_value = {'jobs': [{'name': 'j1'}, {'name': 'j2'}]}
        client.session.request = Mock(return_value=mock_response)
        jobs = client.list_jobs()
        assert len(jobs) == 2

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_build_console(self, mock_session_class, client, mock_response):
        mock_response.text = "Build started\nDone"
        client.session.request = Mock(return_value=mock_response)
        console = client.get_build_console('j', 1)
        assert "Build started" in console

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_trigger_build(self, mock_session_class, client, mock_response):
        mock_response.headers = {'Location': 'https://jenkins.example.com/queue/item/456/'}
        client.session.request = Mock(return_value=mock_response)
        result = client.trigger_build('j')
        assert result['queued'] is True

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_trigger_build_with_params(self, mock_session_class, client, mock_response):
        mock_response.headers = {'Location': 'https://jenkins.example.com/queue/item/456/'}
        client.session.request = Mock(return_value=mock_response)
        result = client.trigger_build('j', {'BRANCH': 'main'})
        assert result['queued'] is True

    # --- Encode job path -------------------------------------------------

    def test_encode_simple(self, client):
        assert client._encode_job_path('simple') == 'simple'

    def test_encode_folder(self, client):
        assert client._encode_job_path('folder/subfolder/job') == 'folder/job/subfolder/job/job'

    def test_encode_spaces(self, client):
        assert 'job%20with%20spaces' in client._encode_job_path('job with spaces')

    # --- New methods (Phase 3) -------------------------------------------

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_pipeline_stages(self, _, client, mock_response):
        mock_response.json.return_value = {'stages': [{'name': 'Build', 'status': 'SUCCESS'}]}
        client.session.request = Mock(return_value=mock_response)
        result = client.get_pipeline_stages('j', 1)
        assert result['stages'][0]['name'] == 'Build'

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_pipeline_stages_404(self, _, client, mock_response):
        from requests import HTTPError
        resp_404 = Mock()
        resp_404.status_code = 404
        exc = HTTPError(response=resp_404)
        mock_response.raise_for_status.side_effect = exc
        mock_response.json.side_effect = exc
        client.session.request = Mock(return_value=mock_response)
        mock_response.raise_for_status.side_effect = exc
        result = client.get_pipeline_stages('j', 1)
        assert 'error' in result

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_job_config(self, _, client, mock_response):
        mock_response.text = '<project/>'
        client.session.request = Mock(return_value=mock_response)
        assert client.get_job_config('j') == '<project/>'

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_update_job_config(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.update_job_config('j', '<project/>')
        assert 'updated' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_create_job(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.create_job('new', '<project/>')
        assert 'created' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_create_job_in_folder(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.create_job('new', '<project/>', folder='myfolder')
        assert 'myfolder/new' in result['message']

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_delete_job(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.delete_job('j')
        assert 'deleted' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_enable_job(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.enable_job('j')
        assert 'enabled' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_disable_job(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.disable_job('j')
        assert 'disabled' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_copy_job(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.copy_job('src', 'dst')
        assert 'copied' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_create_folder(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.create_folder('f')
        assert 'created' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_list_credentials(self, _, client, mock_response):
        mock_response.json.return_value = {'credentials': []}
        client.session.request = Mock(return_value=mock_response)
        result = client.list_credentials()
        assert 'credentials' in result

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_list_views(self, _, client, mock_response):
        mock_response.json.return_value = {'views': [{'name': 'All'}]}
        client.session.request = Mock(return_value=mock_response)
        views = client.list_views()
        assert views[0]['name'] == 'All'

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_view_info(self, _, client, mock_response):
        mock_response.json.return_value = {'name': 'All', 'jobs': []}
        client.session.request = Mock(return_value=mock_response)
        result = client.get_view_info('All')
        assert result['name'] == 'All'

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_get_system_info(self, _, client, mock_response):
        mock_response.json.return_value = {'mode': 'NORMAL', 'numExecutors': 2}
        head_response = Mock()
        head_response.headers = {'X-Jenkins': '2.400'}
        client.session.request = Mock(side_effect=[mock_response, head_response])
        result = client.get_system_info()
        assert result['version'] == '2.400'

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_list_plugins(self, _, client, mock_response):
        mock_response.json.return_value = {'plugins': [{'shortName': 'git', 'version': '5.0'}]}
        client.session.request = Mock(return_value=mock_response)
        plugins = client.list_plugins()
        assert plugins[0]['shortName'] == 'git'

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_replay_build(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.replay_build('j', 1)
        assert 'replay' in result['message'].lower()

    @patch('jenkins_mcp_server.client.requests.Session')
    def test_replay_build_with_script(self, _, client, mock_response):
        client.session.request = Mock(return_value=mock_response)
        result = client.replay_build('j', 1, script='pipeline { agent any }')
        assert 'replay' in result['message'].lower()


# ---------------------------------------------------------------------------
# Job template tests
# ---------------------------------------------------------------------------

class TestJobTemplates:
    """Tests for job XML templates."""

    def test_all_template_keys_exist(self):
        expected = ['freestyle', 'pipeline', 'pipeline-scm', 'multibranch']
        for key in expected:
            assert key in JOB_TEMPLATES

    def test_render_freestyle(self):
        xml = render_job_template('freestyle', description='Test', script='echo hello')
        assert 'echo hello' in xml
        assert '<project>' in xml

    def test_render_pipeline(self):
        xml = render_job_template('pipeline', script='pipeline { agent any }')
        assert 'pipeline { agent any }' in xml
        assert 'flow-definition' in xml

    def test_render_pipeline_scm(self):
        xml = render_job_template(
            'pipeline-scm',
            repo_url='https://github.com/user/repo.git',
            branch='*/main',
            script_path='Jenkinsfile',
        )
        assert 'https://github.com/user/repo.git' in xml
        assert 'Jenkinsfile' in xml

    def test_render_pipeline_scm_with_credential(self):
        xml = render_job_template(
            'pipeline-scm',
            repo_url='https://github.com/user/repo.git',
            credential_id='my-cred',
        )
        assert '<credentialsId>my-cred</credentialsId>' in xml

    def test_render_multibranch(self):
        xml = render_job_template('multibranch', script_path='ci/Jenkinsfile')
        assert 'ci/Jenkinsfile' in xml
        assert 'WorkflowMultiBranchProject' in xml

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            render_job_template('nonexistent')


# ---------------------------------------------------------------------------
# Integration tests (skipped by default)
# ---------------------------------------------------------------------------

class TestJenkinsClientIntegration:
    """Integration tests (require actual Jenkins server)."""

    @pytest.mark.skip(reason="Requires actual Jenkins server")
    def test_real_connection(self):
        import os
        client = JenkinsClient(
            url=os.environ.get('JENKINS_URL', ''),
            username=os.environ.get('JENKINS_USERNAME', ''),
            token=os.environ.get('JENKINS_TOKEN', ''),
            verify_ssl=False,
        )
        assert client.test_connection() is True
