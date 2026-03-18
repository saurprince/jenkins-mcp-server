"""
Jenkins MCP Server for Cursor IDE

A Model Context Protocol (MCP) server that provides Jenkins CI/CD integration
for Cursor IDE and other MCP-compatible AI assistants.

Usage:
    # As MCP server (stdio mode for Cursor)
    jenkins-mcp-server --url URL --username USER --token TOKEN
    
    # As CLI tool
    jenkins-mcp list-jobs
    jenkins-mcp get-build-info --job JOB --build NUMBER
"""

__version__ = "2.0.0"
__author__ = "Suman Saurabh"
__email__ = "saurprince@gmail.com"

from .client import JenkinsClient
from .server import JenkinsMCPServer, TOOLS, ACCESS_LEVELS, get_tools_for_mode

__all__ = [
    "JenkinsClient",
    "JenkinsMCPServer",
    "TOOLS",
    "ACCESS_LEVELS",
    "get_tools_for_mode",
    "__version__",
]
