"""
Tests for Jenkins MCP Server
"""

import json
import pytest
from unittest.mock import Mock, patch

from jenkins_mcp_server.server import JenkinsMCPServer, TOOLS


class TestJenkinsMCPServer:
    """Tests for JenkinsMCPServer class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock JenkinsClient."""
        return Mock()
    
    @pytest.fixture
    def server(self, mock_client):
        """Create a JenkinsMCPServer instance for testing."""
        return JenkinsMCPServer(mock_client)
    
    def test_tools_defined(self):
        """Test that all expected tools are defined."""
        tool_names = [t['name'] for t in TOOLS]
        
        expected_tools = [
            'list_jobs',
            'get_job_details',
            'get_build_info',
            'get_build_console',
            'get_test_report',
            'get_build_parameters',
            'trigger_build',
            'stop_build',
            'get_queue_info',
            'list_nodes',
            'get_node_info',
            'get_artifacts'
        ]
        
        for tool in expected_tools:
            assert tool in tool_names, f"Tool {tool} not found in TOOLS"
    
    def test_tools_have_required_fields(self):
        """Test that all tools have required schema fields."""
        for tool in TOOLS:
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            assert tool['inputSchema']['type'] == 'object'
            assert 'properties' in tool['inputSchema']
            assert 'required' in tool['inputSchema']
    
    def test_handle_initialize(self, server):
        """Test initialize method handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = server.handle_request(request)
        
        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 1
        assert 'result' in response
        assert response['result']['protocolVersion'] == '2024-11-05'
        assert 'tools' in response['result']['capabilities']
    
    def test_handle_tools_list(self, server):
        """Test tools/list method handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = server.handle_request(request)
        
        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 2
        assert 'result' in response
        assert 'tools' in response['result']
        assert len(response['result']['tools']) == len(TOOLS)
    
    def test_handle_tools_call_list_jobs(self, server, mock_client):
        """Test tools/call for list_jobs."""
        mock_client.list_jobs.return_value = [
            {'name': 'job1', 'color': 'blue'},
            {'name': 'job2', 'color': 'red'}
        ]
        
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_jobs",
                "arguments": {}
            }
        }
        
        response = server.handle_request(request)
        
        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 3
        assert 'result' in response
        assert 'content' in response['result']
        
        content = json.loads(response['result']['content'][0]['text'])
        assert content['total'] == 2
        assert len(content['jobs']) == 2
    
    def test_handle_tools_call_get_build_console(self, server, mock_client):
        """Test tools/call for get_build_console."""
        mock_client.get_build_console.return_value = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_build_console",
                "arguments": {
                    "job_name": "test-job",
                    "build_number": 123,
                    "start_line": 1,
                    "max_lines": 2
                }
            }
        }
        
        response = server.handle_request(request)
        
        content = json.loads(response['result']['content'][0]['text'])
        assert content['total_lines'] == 5
        assert content['start_line'] == 1
        assert content['end_line'] == 3
        assert content['truncated'] is True
        assert 'Line 2' in content['console']
        assert 'Line 3' in content['console']
    
    def test_handle_unknown_method(self, server):
        """Test handling of unknown method."""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "unknown/method",
            "params": {}
        }
        
        response = server.handle_request(request)
        
        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 5
        assert 'error' in response
        assert response['error']['code'] == -32601
    
    def test_handle_unknown_tool(self, server):
        """Test handling of unknown tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }
        
        response = server.handle_request(request)
        
        content = json.loads(response['result']['content'][0]['text'])
        assert 'error' in content
        assert 'Unknown tool' in content['error']
    
    def test_handle_tool_error(self, server, mock_client):
        """Test handling of tool execution error."""
        mock_client.list_jobs.side_effect = Exception("Connection failed")
        
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "list_jobs",
                "arguments": {}
            }
        }
        
        response = server.handle_request(request)
        
        content = json.loads(response['result']['content'][0]['text'])
        assert 'error' in content
        assert 'Connection failed' in content['error']
    
    def test_notifications_initialized_returns_none(self, server):
        """Test that notifications/initialized returns None (no response)."""
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        response = server.handle_request(request)
        
        assert response is None
    
    def test_ping_method(self, server):
        """Test ping method handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "ping",
            "params": {}
        }
        
        response = server.handle_request(request)
        
        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 8
        assert response['result'] == {}
