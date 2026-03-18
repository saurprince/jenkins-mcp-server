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

ACCESS_LEVELS = {
    "read-only": 0,
    "standard": 1,
    "admin": 2,
}

# MCP Tool definitions
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_jobs",
        "description": "List all Jenkins jobs with their status, URLs, and last build info",
        "mode": "read-only",
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
        "mode": "read-only",
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
        "mode": "read-only",
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
        "mode": "read-only",
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
        "mode": "read-only",
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
        "mode": "read-only",
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
        "mode": "standard",
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
        "mode": "standard",
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
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_nodes",
        "description": "List all Jenkins nodes/agents with their status and configuration",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_node_info",
        "description": "Get information about a specific Jenkins node/agent",
        "mode": "read-only",
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
        "mode": "read-only",
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

    # --- Phase 2: previously hidden client methods -----------------------

    {
        "name": "get_coverage_report",
        "description": "Get code coverage report for a build (requires coverage plugin)",
        "mode": "read-only",
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
        "name": "get_queue_item",
        "description": "Get details about a specific item in the Jenkins build queue",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queue_id": {
                    "type": "integer",
                    "description": "Queue item ID (returned when a build is triggered)"
                }
            },
            "required": ["queue_id"]
        }
    },
    {
        "name": "get_progressive_console",
        "description": "Get progressive (streaming) console output for a live build, starting from a byte offset",
        "mode": "read-only",
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
                "start": {
                    "type": "integer",
                    "description": "Byte offset to start reading from (0 for beginning)",
                    "default": 0
                }
            },
            "required": ["job_name", "build_number"]
        }
    },

    # --- Phase 4: new read-only tools ------------------------------------

    {
        "name": "get_pipeline_stages",
        "description": "Get Pipeline stage breakdown with status, duration, and steps for a build",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Pipeline job"
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
        "name": "get_job_config",
        "description": "Get the raw XML configuration of a Jenkins job",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "list_credentials",
        "description": "List credential IDs in Jenkins (values are never exposed)",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Credential domain (default: _ for global)",
                    "default": "_"
                }
            },
            "required": []
        }
    },
    {
        "name": "list_views",
        "description": "List all views configured on the Jenkins instance",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_view_info",
        "description": "Get detailed information about a Jenkins view including its jobs",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {
                "view_name": {
                    "type": "string",
                    "description": "Name of the view"
                }
            },
            "required": ["view_name"]
        }
    },
    {
        "name": "get_system_info",
        "description": "Get Jenkins system information including version, executor count, and mode",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_plugins",
        "description": "List installed Jenkins plugins with name, version, and status",
        "mode": "read-only",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    # --- Phase 4: admin-only tools ---------------------------------------

    {
        "name": "create_job",
        "description": "Create a new Jenkins job from XML config or a built-in template (freestyle, pipeline, pipeline-scm, multibranch)",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name for the new job"
                },
                "config_xml": {
                    "type": "string",
                    "description": "Raw XML configuration (takes priority over template)"
                },
                "template": {
                    "type": "string",
                    "enum": ["freestyle", "pipeline", "pipeline-scm", "multibranch"],
                    "description": "Built-in template to use if config_xml is not provided"
                },
                "description": {
                    "type": "string",
                    "description": "Job description (used with template)"
                },
                "script": {
                    "type": "string",
                    "description": "Shell command (freestyle) or Groovy pipeline script (pipeline template)"
                },
                "repo_url": {
                    "type": "string",
                    "description": "Git repository URL (pipeline-scm template)"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch specifier (pipeline-scm template, default: */main)"
                },
                "script_path": {
                    "type": "string",
                    "description": "Path to Jenkinsfile (pipeline-scm/multibranch, default: Jenkinsfile)"
                },
                "credential_id": {
                    "type": "string",
                    "description": "Jenkins credential ID for SCM access"
                },
                "folder": {
                    "type": "string",
                    "description": "Folder to create the job in"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "delete_job",
        "description": "Delete a Jenkins job permanently",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the job to delete"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "enable_job",
        "description": "Enable a disabled Jenkins job",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the job to enable"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "disable_job",
        "description": "Disable a Jenkins job (prevents new builds)",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the job to disable"
                }
            },
            "required": ["job_name"]
        }
    },
    {
        "name": "copy_job",
        "description": "Copy an existing Jenkins job to create a new one",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_name": {
                    "type": "string",
                    "description": "Name of the job to copy from"
                },
                "new_name": {
                    "type": "string",
                    "description": "Name for the new job"
                }
            },
            "required": ["source_name", "new_name"]
        }
    },
    {
        "name": "update_job_config",
        "description": "Update a job's XML configuration",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Jenkins job"
                },
                "config_xml": {
                    "type": "string",
                    "description": "New XML configuration content"
                }
            },
            "required": ["job_name", "config_xml"]
        }
    },
    {
        "name": "create_folder",
        "description": "Create a new folder in Jenkins for organizing jobs",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder_name": {
                    "type": "string",
                    "description": "Name for the new folder"
                },
                "parent": {
                    "type": "string",
                    "description": "Optional parent folder path"
                }
            },
            "required": ["folder_name"]
        }
    },
    {
        "name": "replay_build",
        "description": "Replay a Pipeline build, optionally with a modified Groovy script",
        "mode": "admin",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_name": {
                    "type": "string",
                    "description": "Name of the Pipeline job"
                },
                "build_number": {
                    "type": "integer",
                    "description": "Build number to replay"
                },
                "script": {
                    "type": "string",
                    "description": "Optional modified Groovy pipeline script"
                }
            },
            "required": ["job_name", "build_number"]
        }
    },
]


def get_tools_for_mode(mode: str) -> List[Dict[str, Any]]:
    """Return tool definitions accessible at the given access mode.

    Tools are filtered so that only those whose required access level
    is at or below the requested mode are included.  The ``mode``
    metadata key is stripped from the returned dicts so that MCP
    clients receive a clean schema.
    """
    max_level = ACCESS_LEVELS.get(mode, ACCESS_LEVELS["standard"])
    filtered = []
    for tool in TOOLS:
        if ACCESS_LEVELS.get(tool.get("mode", "read-only"), 0) <= max_level:
            clean = {k: v for k, v in tool.items() if k != "mode"}
            filtered.append(clean)
    return filtered


def _tool_mode_map() -> Dict[str, str]:
    """Build a mapping of tool name -> required mode from TOOLS."""
    return {t["name"]: t.get("mode", "read-only") for t in TOOLS}


class JenkinsMCPServer:
    """MCP Server implementing the Model Context Protocol for Jenkins.
    
    This server provides tools for interacting with Jenkins CI/CD systems
    through the MCP protocol, enabling AI assistants to manage builds,
    view logs, and trigger jobs.
    
    Args:
        client: JenkinsClient instance for API communication
        mode: Access mode -- "read-only", "standard", or "admin"
    
    Example:
        >>> client = JenkinsClient(url, username, token)
        >>> server = JenkinsMCPServer(client, mode="standard")
        >>> server.run_stdio()  # Start MCP server
    """
    
    def __init__(self, client: JenkinsClient, mode: str = "standard"):
        """Initialize MCP server with Jenkins client."""
        self.client = client
        if mode not in ACCESS_LEVELS:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: {', '.join(ACCESS_LEVELS)}")
        self.mode = mode
        self._tool_modes = _tool_mode_map()
    
    def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool and return the result.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        required_mode = self._tool_modes.get(name)
        if required_mode is None:
            return {"error": f"Unknown tool: {name}"}
        if ACCESS_LEVELS.get(required_mode, 0) > ACCESS_LEVELS.get(self.mode, 1):
            return {
                "error": (
                    f"Tool '{name}' requires '{required_mode}' mode, "
                    f"but server is running in '{self.mode}' mode. "
                    f"Restart with --mode {required_mode} to enable this tool."
                )
            }
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

            # Phase 2: previously hidden methods
            elif name == "get_coverage_report":
                return self.client.get_coverage_report(
                    arguments["job_name"],
                    arguments["build_number"]
                )

            elif name == "get_queue_item":
                return self.client.get_queue_item(arguments["queue_id"])

            elif name == "get_progressive_console":
                return self.client.get_progressive_console(
                    arguments["job_name"],
                    arguments["build_number"],
                    start=arguments.get("start", 0)
                )

            # Phase 4: new read-only tools
            elif name == "get_pipeline_stages":
                return self.client.get_pipeline_stages(
                    arguments["job_name"],
                    arguments["build_number"]
                )

            elif name == "get_job_config":
                config = self.client.get_job_config(arguments["job_name"])
                return {"job_name": arguments["job_name"], "config_xml": config}

            elif name == "list_credentials":
                return self.client.list_credentials(
                    domain=arguments.get("domain", "_")
                )

            elif name == "list_views":
                views = self.client.list_views()
                return {"total": len(views), "views": views}

            elif name == "get_view_info":
                return self.client.get_view_info(arguments["view_name"])

            elif name == "get_system_info":
                return self.client.get_system_info()

            elif name == "list_plugins":
                plugins = self.client.list_plugins()
                return {"total": len(plugins), "plugins": plugins}

            # Phase 4: admin tools
            elif name == "create_job":
                config_xml = arguments.get("config_xml")
                if not config_xml:
                    from .client import render_job_template
                    template = arguments.get("template", "freestyle")
                    config_xml = render_job_template(
                        template=template,
                        description=arguments.get("description", ""),
                        script=arguments.get("script", ""),
                        repo_url=arguments.get("repo_url", ""),
                        branch=arguments.get("branch", "*/main"),
                        script_path=arguments.get("script_path", "Jenkinsfile"),
                        credential_id=arguments.get("credential_id", ""),
                    )
                return self.client.create_job(
                    arguments["job_name"],
                    config_xml,
                    folder=arguments.get("folder"),
                )

            elif name == "delete_job":
                return self.client.delete_job(arguments["job_name"])

            elif name == "enable_job":
                return self.client.enable_job(arguments["job_name"])

            elif name == "disable_job":
                return self.client.disable_job(arguments["job_name"])

            elif name == "copy_job":
                return self.client.copy_job(
                    arguments["source_name"],
                    arguments["new_name"]
                )

            elif name == "update_job_config":
                return self.client.update_job_config(
                    arguments["job_name"],
                    arguments["config_xml"]
                )

            elif name == "create_folder":
                return self.client.create_folder(
                    arguments["folder_name"],
                    parent=arguments.get("parent"),
                )

            elif name == "replay_build":
                return self.client.replay_build(
                    arguments["job_name"],
                    arguments["build_number"],
                    script=arguments.get("script"),
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
                            "name": "jenkins-mcp-server",
                            "version": "2.0.1"
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
                    "result": {"tools": get_tools_for_mode(self.mode)}
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
  JENKINS_MODE        Access mode: read-only, standard (default), admin

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
        '--mode',
        choices=['read-only', 'standard', 'admin'],
        default=None,
        help='Access mode: read-only (view only), standard (default, +trigger/stop), admin (full control)'
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
    
    mode = args.mode or os.environ.get('JENKINS_MODE', 'standard')
    server = JenkinsMCPServer(client, mode=mode)
    logger.info(f"Access mode: {mode}")
    
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
