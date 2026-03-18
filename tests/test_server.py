"""
Tests for Jenkins MCP Server
"""

import json
import pytest
from unittest.mock import Mock, patch

from jenkins_mcp_server.server import (
    JenkinsMCPServer,
    TOOLS,
    ACCESS_LEVELS,
    get_tools_for_mode,
    _tool_mode_map,
)


# ---------------------------------------------------------------------------
# Tool definition tests
# ---------------------------------------------------------------------------

class TestToolDefinitions:
    """Validate the TOOLS list and metadata."""

    EXPECTED_TOOLS = [
        # read-only (original)
        'list_jobs', 'get_job_details', 'get_build_info', 'get_build_console',
        'get_test_report', 'get_build_parameters', 'get_queue_info',
        'list_nodes', 'get_node_info', 'get_artifacts',
        # read-only (phase 2 - previously hidden)
        'get_coverage_report', 'get_queue_item', 'get_progressive_console',
        # read-only (phase 4 - new)
        'get_pipeline_stages', 'get_job_config', 'list_credentials',
        'list_views', 'get_view_info', 'get_system_info', 'list_plugins',
        # standard
        'trigger_build', 'stop_build',
        # admin
        'create_job', 'delete_job', 'enable_job', 'disable_job',
        'copy_job', 'update_job_config', 'create_folder', 'replay_build',
    ]

    def test_all_expected_tools_present(self):
        tool_names = [t['name'] for t in TOOLS]
        for name in self.EXPECTED_TOOLS:
            assert name in tool_names, f"Tool {name} missing from TOOLS"

    def test_tools_have_required_fields(self):
        for tool in TOOLS:
            assert 'name' in tool
            assert 'description' in tool
            assert 'mode' in tool
            assert tool['mode'] in ACCESS_LEVELS
            assert 'inputSchema' in tool
            assert tool['inputSchema']['type'] == 'object'
            assert 'properties' in tool['inputSchema']
            assert 'required' in tool['inputSchema']

    def test_total_tool_count(self):
        assert len(TOOLS) == len(self.EXPECTED_TOOLS)


# ---------------------------------------------------------------------------
# Access mode tests
# ---------------------------------------------------------------------------

class TestAccessModes:
    """Validate mode-based tool filtering."""

    def test_read_only_filters_write_tools(self):
        tools = get_tools_for_mode("read-only")
        names = {t['name'] for t in tools}
        assert 'list_jobs' in names
        assert 'trigger_build' not in names
        assert 'create_job' not in names

    def test_standard_includes_trigger_stop(self):
        tools = get_tools_for_mode("standard")
        names = {t['name'] for t in tools}
        assert 'trigger_build' in names
        assert 'stop_build' in names
        assert 'create_job' not in names

    def test_admin_includes_everything(self):
        tools = get_tools_for_mode("admin")
        names = {t['name'] for t in tools}
        assert 'list_jobs' in names
        assert 'trigger_build' in names
        assert 'create_job' in names
        assert 'delete_job' in names
        assert len(tools) == len(TOOLS)

    def test_read_only_tool_count(self):
        tools = get_tools_for_mode("read-only")
        assert len(tools) == 20

    def test_standard_tool_count(self):
        tools = get_tools_for_mode("standard")
        assert len(tools) == 22

    def test_admin_tool_count(self):
        tools = get_tools_for_mode("admin")
        assert len(tools) == len(TOOLS)

    def test_mode_field_stripped_from_output(self):
        for tool in get_tools_for_mode("admin"):
            assert 'mode' not in tool

    def test_tool_mode_map(self):
        mapping = _tool_mode_map()
        assert mapping['list_jobs'] == 'read-only'
        assert mapping['trigger_build'] == 'standard'
        assert mapping['create_job'] == 'admin'


# ---------------------------------------------------------------------------
# Server class tests
# ---------------------------------------------------------------------------

class TestJenkinsMCPServer:
    """Tests for JenkinsMCPServer class."""

    @pytest.fixture
    def mock_client(self):
        return Mock()

    @pytest.fixture
    def server(self, mock_client):
        return JenkinsMCPServer(mock_client, mode="admin")

    @pytest.fixture
    def readonly_server(self, mock_client):
        return JenkinsMCPServer(mock_client, mode="read-only")

    def test_invalid_mode_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid mode"):
            JenkinsMCPServer(mock_client, mode="superuser")

    # --- Protocol handling -----------------------------------------------

    def test_handle_initialize(self, server):
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        response = server.handle_request(request)
        assert response['result']['protocolVersion'] == '2024-11-05'
        assert response['result']['serverInfo']['version'] == '2.0.0'

    def test_handle_tools_list_respects_mode(self, readonly_server):
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = readonly_server.handle_request(request)
        tool_names = {t['name'] for t in response['result']['tools']}
        assert 'list_jobs' in tool_names
        assert 'trigger_build' not in tool_names

    def test_notifications_initialized_returns_none(self, server):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        assert server.handle_request(request) is None

    def test_ping_method(self, server):
        request = {"jsonrpc": "2.0", "id": 8, "method": "ping", "params": {}}
        response = server.handle_request(request)
        assert response['result'] == {}

    def test_unknown_method(self, server):
        request = {"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}}
        response = server.handle_request(request)
        assert response['error']['code'] == -32601

    # --- Mode enforcement ------------------------------------------------

    def test_readonly_rejects_trigger(self, readonly_server):
        result = readonly_server.handle_tool_call("trigger_build", {"job_name": "x"})
        assert 'error' in result
        assert "read-only" in result['error']

    def test_readonly_rejects_admin_tool(self, readonly_server):
        result = readonly_server.handle_tool_call("create_job", {"job_name": "x"})
        assert 'error' in result

    def test_standard_rejects_admin_tool(self, mock_client):
        server = JenkinsMCPServer(mock_client, mode="standard")
        result = server.handle_tool_call("delete_job", {"job_name": "x"})
        assert 'error' in result
        assert "admin" in result['error']

    # --- Original tool dispatch ------------------------------------------

    def test_list_jobs(self, server, mock_client):
        mock_client.list_jobs.return_value = [{'name': 'j1'}, {'name': 'j2'}]
        result = server.handle_tool_call("list_jobs", {})
        assert result['total'] == 2

    def test_get_job_details(self, server, mock_client):
        mock_client.get_job_details.return_value = {'name': 'j1'}
        result = server.handle_tool_call("get_job_details", {"job_name": "j1"})
        assert result['name'] == 'j1'

    def test_get_build_console_pagination(self, server, mock_client):
        mock_client.get_build_console.return_value = "L1\nL2\nL3\nL4\nL5"
        result = server.handle_tool_call("get_build_console", {
            "job_name": "j", "build_number": 1, "start_line": 1, "max_lines": 2
        })
        assert result['start_line'] == 1
        assert result['lines_returned'] == 2
        assert result['truncated'] is True

    def test_trigger_build(self, server, mock_client):
        mock_client.trigger_build.return_value = {'queued': True}
        result = server.handle_tool_call("trigger_build", {"job_name": "j"})
        assert result['queued'] is True

    # --- New tool dispatch -----------------------------------------------

    def test_get_coverage_report(self, server, mock_client):
        mock_client.get_coverage_report.return_value = {'line': 85}
        result = server.handle_tool_call("get_coverage_report", {"job_name": "j", "build_number": 1})
        assert result['line'] == 85

    def test_get_queue_item(self, server, mock_client):
        mock_client.get_queue_item.return_value = {'id': 42}
        result = server.handle_tool_call("get_queue_item", {"queue_id": 42})
        assert result['id'] == 42

    def test_get_progressive_console(self, server, mock_client):
        mock_client.get_progressive_console.return_value = {'text': 'hi', 'hasMoreData': False}
        result = server.handle_tool_call("get_progressive_console", {"job_name": "j", "build_number": 1})
        assert result['text'] == 'hi'

    def test_get_pipeline_stages(self, server, mock_client):
        mock_client.get_pipeline_stages.return_value = {'stages': []}
        result = server.handle_tool_call("get_pipeline_stages", {"job_name": "j", "build_number": 1})
        assert 'stages' in result

    def test_get_job_config(self, server, mock_client):
        mock_client.get_job_config.return_value = '<project/>'
        result = server.handle_tool_call("get_job_config", {"job_name": "j"})
        assert result['config_xml'] == '<project/>'

    def test_list_credentials(self, server, mock_client):
        mock_client.list_credentials.return_value = {'credentials': []}
        result = server.handle_tool_call("list_credentials", {})
        assert 'credentials' in result

    def test_list_views(self, server, mock_client):
        mock_client.list_views.return_value = [{'name': 'All'}]
        result = server.handle_tool_call("list_views", {})
        assert result['total'] == 1

    def test_get_view_info(self, server, mock_client):
        mock_client.get_view_info.return_value = {'name': 'All'}
        result = server.handle_tool_call("get_view_info", {"view_name": "All"})
        assert result['name'] == 'All'

    def test_get_system_info(self, server, mock_client):
        mock_client.get_system_info.return_value = {'version': '2.400'}
        result = server.handle_tool_call("get_system_info", {})
        assert result['version'] == '2.400'

    def test_list_plugins(self, server, mock_client):
        mock_client.list_plugins.return_value = [{'shortName': 'git'}]
        result = server.handle_tool_call("list_plugins", {})
        assert result['total'] == 1

    def test_create_job_with_template(self, server, mock_client):
        mock_client.create_job.return_value = {'message': 'created'}
        result = server.handle_tool_call("create_job", {
            "job_name": "new-job", "template": "pipeline", "script": "echo hi"
        })
        assert 'created' in result['message']
        call_args = mock_client.create_job.call_args
        assert 'echo hi' in call_args[0][1]

    def test_create_job_with_raw_xml(self, server, mock_client):
        mock_client.create_job.return_value = {'message': 'created'}
        xml = '<project><description>test</description></project>'
        result = server.handle_tool_call("create_job", {"job_name": "j", "config_xml": xml})
        assert mock_client.create_job.call_args[0][1] == xml

    def test_delete_job(self, server, mock_client):
        mock_client.delete_job.return_value = {'message': 'deleted'}
        result = server.handle_tool_call("delete_job", {"job_name": "j"})
        assert 'deleted' in result['message']

    def test_enable_disable_job(self, server, mock_client):
        mock_client.enable_job.return_value = {'message': 'enabled'}
        mock_client.disable_job.return_value = {'message': 'disabled'}
        assert 'enabled' in server.handle_tool_call("enable_job", {"job_name": "j"})['message']
        assert 'disabled' in server.handle_tool_call("disable_job", {"job_name": "j"})['message']

    def test_copy_job(self, server, mock_client):
        mock_client.copy_job.return_value = {'message': 'copied'}
        result = server.handle_tool_call("copy_job", {"source_name": "a", "new_name": "b"})
        assert 'copied' in result['message']

    def test_update_job_config(self, server, mock_client):
        mock_client.update_job_config.return_value = {'message': 'updated'}
        result = server.handle_tool_call("update_job_config", {"job_name": "j", "config_xml": "<x/>"})
        assert 'updated' in result['message']

    def test_create_folder(self, server, mock_client):
        mock_client.create_folder.return_value = {'message': 'created'}
        result = server.handle_tool_call("create_folder", {"folder_name": "f"})
        assert 'created' in result['message']

    def test_replay_build(self, server, mock_client):
        mock_client.replay_build.return_value = {'message': 'replayed'}
        result = server.handle_tool_call("replay_build", {"job_name": "j", "build_number": 1})
        assert 'replayed' in result['message']

    # --- Error handling --------------------------------------------------

    def test_tool_error_returns_message(self, server, mock_client):
        mock_client.list_jobs.side_effect = Exception("Connection failed")
        result = server.handle_tool_call("list_jobs", {})
        assert 'Connection failed' in result['error']

    def test_unknown_tool(self, server):
        result = server.handle_tool_call("nonexistent_tool", {})
        assert 'error' in result
