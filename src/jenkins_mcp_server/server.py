"""
Jenkins MCP Server

Implements the Model Context Protocol (MCP) for Jenkins integration.
This server can be used with Cursor IDE or any MCP-compatible client.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import requests

from .client import JenkinsClient

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# MCP Tool definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_jobs",
        "description": "List all Jenkins jobs with their status, URLs, and last build info",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {
                    "type": "string",
                    "description": "Optional folder path to list jobs from"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_job_details",
        "description": "Get detailed information about a specific Jenkins job including builds, health reports",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job (can include folder path like 'folder/job')"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "get_build_info",
        "description": "Get information about a specific build including status, duration, result, and actions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number"
                }
            },
            "required": ["job_name", "build_number"]
        }
    },
    {
        "name": "get_build_console",
        "description": "Get console output from a Jenkins build with optional line pagination",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (0-indexed)",
                    "default": 0
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to return",
                    "default": 500
                }
            },
            "required": ["job_name", "build_number"]
        }
    },
    {
        "name": "get_test_report",
        "description": "Get test report for a build including pass/fail counts, test suites, and test cases",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number"
                }
            },
            "required": ["job_name", "build_number"]
        }
    },
    {
        "name": "get_build_parameters",
        "description": "Get the parameters used for a specific build",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number"
                }
            },
            "required": ["job_name", "build_number"]
        }
    },
    {
        "name": "trigger_build",
        "description": "Trigger a new build for a Jenkins job with optional parameters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the job to build"
                },
                "parameters": {
                    "type": "object",
                    "description": "Build parameters as key-value pairs"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "stop_build",
        "description": "Stop a running Jenkins build",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number to stop"
                }
            },
            "required": ["job_name", "build_number"]
        }
    },
    {
        "name": "get_queue_info",
        "description": "Get information about the Jenkins build queue including pending builds",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_nodes",
        "description": "List all Jenkins nodes/agents with their status and configuration",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_node_info",
        "description": "Get information about a specific Jenkins node/agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_name": {
                    "type": "string",
                    "description": "Name of the node (use '(master)' for built-in node)"
                }
            },
            "required": ["node_name"]
        }
    },
    {
        "name": "get_artifacts",
        "description": "Get list of artifacts for a build",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number"
                }
            },
            "required": ["job_name", "build_number"]
        }
    }
]


class JenkinsMCPServer:
    """MCP Server implementing the Model Context Protocol for Jenkins.
    
    This server provides tools for interacting with Jenkins CI/CD systems
    through the MCP protocol, enabling AI assistants to manage builds,
    view logs, and trigger jobs.
    
    Args:
        client: JenkinsClient instance for API communication
    
    Example:
        >>> client = JenkinsClient(url, username, token)
        >>> server = JenkinsMCPServer(client)
        >>> server.run_stdio()  # Start MCP server
    """
    
    def __init__(self, client: JenkinsClient):
        """Initialize MCP server with Jenkins client."""
        self.client = client
    
    def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool and return the result.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            if name == "list_jobs":
                jobs = self.client.list_jobs(arguments.get("folder"))
                return {"total": len(jobs), "jobs": jobs}
            
            elif name == "get_job_details":
                return self.client.get_job_details(arguments["job_name"])
            
            elif name == "get_build_info":
                return self.client.get_build_info(
                    arguments["job_name"],
                    arguments["build_number"]
                )
            
            elif name == "get_build_console":
                console = self.client.get_build_console(
                    arguments["job_name"],
                    arguments["build_number"]
                )
                lines = console.split('\n')
                start = arguments.get("start_line", 0)
                max_lines = arguments.get("max_lines", 500)
                end = min(start + max_lines, len(lines))
                return {
                    "job_name": arguments["job_name"],
                    "build_number": arguments["build_number"],
                    "total_lines": len(lines),
                    "start_line": start,
                    "end_line": end,
                    "lines_returned": end - start,
                    "truncated": end < len(lines),
                    "console": '\n'.join(lines[start:end])
                }
            
            elif name == "get_test_report":
                return self.client.get_test_report(
                    arguments["job_name"],
                    arguments["build_number"]
                )
            
            elif name == "get_build_parameters":
                return self.client.get_build_parameters(
                    arguments["job_name"],
                    arguments["build_number"]
                )
            
            elif name == "trigger_build":
                return self.client.trigger_build(
                    arguments["job_name"],
                    arguments.get("parameters")
                )
            
            elif name == "stop_build":
                return self.client.stop_build(
                    arguments["job_name"],
                    arguments["build_number"]
                )
            
            elif name == "get_queue_info":
                return self.client.get_queue_info()
            
            elif name == "list_nodes":
                nodes = self.client.list_nodes()
                return {"total": len(nodes), "nodes": nodes}
            
            elif name == "get_node_info":
                return self.client.get_node_info(arguments["node_name"])
            
            elif name == "get_artifacts":
                return self.client.get_artifacts(
                    arguments["job_name"],
                    arguments["build_number"]
                )
            
            else:
                return {"error": f"Unknown tool: {name}"}
                
        except requests.HTTPError as e:
            error_text = e.response.text[:500] if e.response.text else "No details"
            return {"error": f"HTTP {e.response.status_code}: {error_text}"}
        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return {"error": str(e)}
    
    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an MCP JSON-RPC request.
        
        Args:
            request: JSON-RPC request dictionary
            
        Returns:
            JSON-RPC response or None for notifications
        """
        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})
        
        try:
            if method == "initialize":
                # MCP initialization handshake
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "druva-jenkins-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "notifications/initialized":
                # Client notification - no response needed
                return None
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": TOOLS}
                }
            
            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = self.handle_tool_call(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ]
                    }
                }
            
            elif method == "ping":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {}
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                
        except Exception as e:
            logger.exception("Error handling request")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)}
            }
    
    def run_stdio(self):
        """Run the MCP server in stdio mode.
        
        Reads JSON-RPC requests from stdin and writes responses to stdout.
        This is the standard mode for Cursor IDE integration.
        """
        logger.info("Jenkins MCP server started in stdio mode")
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                logger.debug(f"Received: {request.get('method', 'unknown')}")
                
                response = self.handle_request(request)
                
                if response is not None:
                    print(json.dumps(response), flush=True)
                    
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                logger.exception("Error processing request")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                }
                print(json.dumps(error_response), flush=True)


def create_client_from_args(args: argparse.Namespace) -> JenkinsClient:
    """Create JenkinsClient from parsed arguments.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Configured JenkinsClient
        
    Raises:
        ValueError: If required arguments are missing
    """
    url = args.url or os.environ.get('JENKINS_URL')
    username = args.username or os.environ.get('JENKINS_USERNAME')
    token = args.token or os.environ.get('JENKINS_TOKEN')
    verify_ssl = not (args.no_verify_ssl or 
                      os.environ.get('JENKINS_VERIFY_SSL', 'true').lower() == 'false')
    
    if not all([url, username, token]):
        missing = []
        if not url:
            missing.append("JENKINS_URL or --url")
        if not username:
            missing.append("JENKINS_USERNAME or --username")
        if not token:
            missing.append("JENKINS_TOKEN or --token")
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    return JenkinsClient(url, username, token, verify_ssl)


def main():
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(
        description='Jenkins MCP Server for Cursor IDE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  JENKINS_URL         Jenkins server URL
  JENKINS_USERNAME    Jenkins username
  JENKINS_TOKEN       Jenkins API token
  JENKINS_VERIFY_SSL  Set to 'false' to disable SSL verification

Examples:
  # Run as MCP server (for Cursor)
  jenkins-mcp-server --url URL --username USER --token TOKEN --no-verify-ssl
  
  # Test connection
  jenkins-mcp-server --test --url URL --username USER --token TOKEN
  
  # Execute single tool (for debugging)
  jenkins-mcp-server --tool list_jobs --url URL --username USER --token TOKEN
"""
    )
    parser.add_argument(
        '--url',
        help='Jenkins server URL (or set JENKINS_URL)'
    )
    parser.add_argument(
        '--username',
        help='Jenkins username (or set JENKINS_USERNAME)'
    )
    parser.add_argument(
        '--token',
        help='Jenkins API token (or set JENKINS_TOKEN)'
    )
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test connection and exit'
    )
    parser.add_argument(
        '--tool',
        help='Execute a specific tool (for debugging)'
    )
    parser.add_argument(
        '--args',
        help='Tool arguments as JSON string'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        client = create_client_from_args(args)
    except ValueError as e:
        parser.error(str(e))
        return 1
    
    server = JenkinsMCPServer(client)
    
    # Test mode
    if args.test:
        logger.info(f"Testing connection to {client.url}")
        try:
            jobs = client.list_jobs()
            logger.info(f"Connection successful! Found {len(jobs)} jobs")
            for job in jobs[:5]:
                status = job.get('color', 'unknown')
                logger.info(f"  - {job['name']} ({status})")
            if len(jobs) > 5:
                logger.info(f"  ... and {len(jobs) - 5} more")
            return 0
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return 1
    
    # Single tool execution mode
    if args.tool:
        tool_args = json.loads(args.args) if args.args else {}
        result = server.handle_tool_call(args.tool, tool_args)
        print(json.dumps(result, indent=2))
        return 0
    
    # Run MCP server in stdio mode
    server.run_stdio()
    return 0


if __name__ == '__main__':
    sys.exit(main())
