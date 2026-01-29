# Jenkins MCP Server

A Model Context Protocol (MCP) server that provides Jenkins CI/CD integration for Cursor IDE and other MCP-compatible AI assistants.

## Features

- **MCP Protocol Support**: Full MCP stdio protocol implementation for Cursor IDE
- **CLI Tool**: Command-line interface for quick Jenkins queries
- **Comprehensive API**: Access jobs, builds, console logs, test reports, and more
- **Python 3.7+**: Compatible with Python 3.7 and later

## Installation

### Quick Install (Recommended)

```bash
# Install directly from GitLab
pip install git+https://git.druva.org/credits/jenkins-mcp-server.git

# Or via SSH
pip install git+ssh://git@git.druva.org/credits/jenkins-mcp-server.git
```

### From Source

```bash
# Clone the repository
git clone https://git.druva.org/credits/jenkins-mcp-server.git
cd jenkins-mcp-server

# Install
pip install .
```

## Configuration

### Environment Variables

Set these environment variables for authentication:

```bash
export JENKINS_URL="https://your-jenkins-server.example.com:8443"
export JENKINS_USERNAME="your-username"
export JENKINS_TOKEN="your-api-token"
export JENKINS_VERIFY_SSL="false"  # Optional: for self-signed certificates
```

### Getting a Jenkins API Token

Jenkins API tokens are used for authentication instead of passwords when accessing Jenkins via CLI or REST API. Follow these steps to generate one:

#### Step-by-Step Instructions

1. **Log in to Jenkins**
   - Open your Jenkins server URL in a browser (e.g., `https://your-jenkins-server.example.com:8443`)
   - Log in with your credentials

2. **Navigate to User Configuration**
   - Click your **username** in the top-right corner of the Jenkins dashboard
   - Select **Configure** from the dropdown menu (or click your name → Configure)

3. **Generate API Token**
   - Scroll down to the **API Token** section
   - Click **Add new Token**
   - Enter a descriptive name for your token (e.g., `cursor-mcp-server`, `ci-automation`)
   - Click **Generate**

4. **Copy and Save the Token**
   - **Important**: Copy the token immediately — it will only be displayed once!
   - Store it securely (e.g., password manager, environment variable)
   - The token is now ready to use

#### Best Practices for API Tokens

- **Create separate tokens** for different purposes (IDE integration, CI pipelines, scripts)
- **Use descriptive names** so you can identify tokens later
- **Revoke unused tokens** from the same Configure page if compromised or no longer needed
- **Tokens don't expire** by default, but you can regenerate/revoke them anytime without changing your password

#### Troubleshooting Token Generation

| Issue | Solution |
|-------|----------|
| No "API Token" section visible | Your Jenkins admin may have disabled token generation. Contact your admin. |
| Token generation fails | Check if you have sufficient permissions. Some Jenkins instances restrict this. |
| Using CloudBees CI | Generate tokens on the Operations Center, not on individual controllers. |

## Usage

### As MCP Server (for Cursor IDE)

#### Method 1: Global Cursor Configuration

Add to `~/.cursor/mcp.json` (Linux/Mac) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp-server",
      "args": [
        "--url", "https://your-jenkins-server.example.com:8443",
        "--username", "your-username",
        "--token", "your-api-token",
        "--no-verify-ssl"
      ],
      "disabled": false,
      "timeout": 60
    }
  }
}
```

#### Method 2: Using Environment Variables

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp-server",
      "args": ["--no-verify-ssl"],
      "env": {
        "JENKINS_URL": "https://your-jenkins-server.example.com:8443",
        "JENKINS_USERNAME": "your-username",
        "JENKINS_TOKEN": "your-api-token"
      }
    }
  }
}
```

#### Method 3: Workspace-specific Configuration

Create `.cursor/mcp.json` in your project root with the same format.

After configuration, restart Cursor or reload MCP servers (Cmd/Ctrl+Shift+P → "MCP: Reload Servers").

### As CLI Tool

```bash
# List all jobs
jenkins-mcp list-jobs

# List jobs with simple format
jenkins-mcp list-jobs -f simple

# Get build information
jenkins-mcp get-build --job MyJob --build 64

# Get test report summary
jenkins-mcp get-test-report --job MyJob --build 64 --summary

# Get console output (last 100 lines)
jenkins-mcp get-console --job MyJob --build 64 --tail 100

# Trigger a build
jenkins-mcp trigger-build MyJob

# Trigger with parameters
jenkins-mcp trigger-build MyJob --parameters '{"BRANCH": "master", "ENV": "staging"}'

# Stop a running build
jenkins-mcp stop-build --job MyJob --build 123
```

### Available MCP Tools

When used with Cursor IDE, the following tools are available:

| Tool | Description |
|------|-------------|
| `list_jobs` | List all Jenkins jobs with status |
| `get_job_details` | Get detailed job information |
| `get_build_info` | Get build status, duration, result |
| `get_build_console` | Get console output (with pagination) |
| `get_test_report` | Get test pass/fail counts and details |
| `get_build_parameters` | Get parameters used for a build |
| `trigger_build` | Trigger a new build |
| `stop_build` | Stop a running build |
| `get_queue_info` | Get build queue information |
| `list_nodes` | List Jenkins nodes/agents |
| `get_node_info` | Get specific node details |
| `get_artifacts` | List build artifacts |

### Example Prompts for Cursor

Once configured, you can ask Cursor things like:

- "List all Jenkins jobs"
- "Get the test report for MyJob build 64"
- "Show me the console output for the last build of MyJob"
- "What are the build parameters for MyJob build 64?"
- "Trigger a new build for MyJob with BRANCH=feature-x"

## Python API

```python
from jenkins_mcp_server import JenkinsClient

# Create client
client = JenkinsClient(
    url="https://your-jenkins-server.example.com:8443",
    username="your-username",
    token="your-api-token",
    verify_ssl=False
)

# List jobs
jobs = client.list_jobs()
for job in jobs:
    print(f"{job['name']}: {job.get('color', 'unknown')}")

# Get build info
build = client.get_build_info("MyJob", 64)
print(f"Result: {build.get('result')}")
print(f"Duration: {build.get('duration')}ms")

# Get test report
report = client.get_test_report("MyJob", 64)
print(f"Passed: {report.get('passCount')}")
print(f"Failed: {report.get('failCount')}")

# Get console output
console = client.get_build_console("MyJob", 64)
print(console[-1000:])  # Last 1000 characters

# Trigger a build
result = client.trigger_build("MyJob", {"BRANCH": "master"})
print(f"Queued: {result['queue_url']}")
```

## Troubleshooting

### MCP Server Not Loading in Cursor

1. Check if the package is installed: `pip show jenkins-mcp-server`
2. Verify the command works: `jenkins-mcp-server --test --url URL --username USER --token TOKEN --no-verify-ssl`
3. Check Cursor's Output panel for MCP errors
4. Restart Cursor after changing mcp.json

### SSL Certificate Errors

Use `--no-verify-ssl` flag or set `JENKINS_VERIFY_SSL=false` for self-signed certificates.

### Authentication Errors (401)

1. Verify your username and token are correct
2. Ensure the API token hasn't expired or been revoked
3. Check if your account has API access permissions
4. Try regenerating the API token from Jenkins

### Connection Timeouts

1. Ensure VPN is connected (if required for your Jenkins server)
2. Check if Jenkins server is accessible: `curl -I https://your-jenkins-server.example.com:8443`

## Contributing

1. Clone the repository
2. Create a feature branch
3. Make your changes
4. Create a merge request

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions, open an issue on the repository.
