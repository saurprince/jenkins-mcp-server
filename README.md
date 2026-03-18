# Jenkins MCP Server

A Model Context Protocol (MCP) server that provides Jenkins CI/CD integration for **Cursor IDE** and other MCP-compatible AI assistants.

## Features

- **27 MCP tools** covering jobs, builds, pipelines, nodes, credentials, views, system info, and more
- **3 access modes** -- `read-only`, `standard`, `admin` -- so you can share safely with any audience
- **Job creation from templates** -- create Freestyle, Pipeline, Pipeline-SCM, and Multibranch jobs without writing XML
- **CLI tool** for quick Jenkins queries from the terminal
- **Python 3.7+** compatible

## Quick Start

```bash
# 1. Install
pip install git+https://github.com/saurprince/jenkins-mcp-server.git

# 2. Test connection
jenkins-mcp-server --test \
  --url https://your-jenkins.example.com:8443 \
  --username your-username \
  --token your-api-token \
  --no-verify-ssl

# 3. Add to Cursor (see "Cursor IDE Integration" below)
```

## Installation

### From GitHub (Recommended)

```bash
pip install git+https://github.com/saurprince/jenkins-mcp-server.git

# Or via SSH
pip install git+ssh://git@github.com/saurprince/jenkins-mcp-server.git
```

### From Source

```bash
git clone https://github.com/saurprince/jenkins-mcp-server.git
cd jenkins-mcp-server
pip install .
```

## Sharing with Your Team

There are several ways to distribute the server to others:

### Option A: Install from Git

Anyone with access to the GitHub repo can install directly:

```bash
pip install git+https://github.com/saurprince/jenkins-mcp-server.git
```

### Option B: Share a wheel file

Build a wheel and send the `.whl` file to teammates:

```bash
pip install build
python -m build --wheel
# Share dist/jenkins_mcp_server-2.0.0-py3-none-any.whl
```

Recipients install with:

```bash
pip install jenkins_mcp_server-2.0.0-py3-none-any.whl
```

### Option C: Private PyPI / Artifactory

Upload the wheel to a private package index:

```bash
pip install twine
twine upload --repository internal dist/*.whl
```

Then anyone can `pip install jenkins-mcp-server` from the internal index.

### Option D: Public PyPI

```bash
pip install twine
twine upload dist/*.whl
```

Then anyone in the world can `pip install jenkins-mcp-tools`.

## Access Modes

The server supports three access modes, controlled via `--mode` flag or `JENKINS_MODE` environment variable:

| Mode | Tools Available | Use Case |
|------|----------------|----------|
| `read-only` | 20 read-only tools | Safe for analysts, viewers, dashboards |
| `standard` (default) | 22 tools (read + trigger/stop builds) | Day-to-day developer use |
| `admin` | All 27+ tools (read + write + create/delete) | Jenkins administrators |

### Read-only mode (safe sharing)

```bash
jenkins-mcp-server --mode read-only --url URL --username USER --token TOKEN
```

In read-only mode, any attempt to call `trigger_build`, `stop_build`, `create_job`, etc. returns a clear error message explaining which mode is required.

### Standard mode (default)

```bash
jenkins-mcp-server --url URL --username USER --token TOKEN
```

Allows triggering and stopping builds, but not creating, deleting, or configuring jobs.

### Admin mode

```bash
jenkins-mcp-server --mode admin --url URL --username USER --token TOKEN
```

Full access including job creation, deletion, configuration changes, folder management, and build replay.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JENKINS_URL` | Jenkins server URL | (required) |
| `JENKINS_USERNAME` | Jenkins username | (required) |
| `JENKINS_TOKEN` | Jenkins API token | (required) |
| `JENKINS_VERIFY_SSL` | `false` to disable SSL verification | `true` |
| `JENKINS_MODE` | Access mode: `read-only`, `standard`, `admin` | `standard` |

### Getting a Jenkins API Token

1. Log in to Jenkins in your browser
2. Click your **username** (top-right) → **Configure**
3. Scroll to **API Token** → **Add new Token**
4. Name it (e.g., `cursor-mcp-server`) → **Generate**
5. Copy immediately -- it's shown only once

## Cursor IDE Integration

### Global Configuration

Add to `~/.cursor/mcp.json` (Linux/Mac) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

#### Standard mode (default for developers)

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp-server",
      "args": [
        "--url", "https://your-jenkins.example.com:8443",
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

#### Read-only mode (safe for sharing with analysts)

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp-server",
      "args": [
        "--url", "https://your-jenkins.example.com:8443",
        "--username", "viewer-username",
        "--token", "viewer-api-token",
        "--no-verify-ssl",
        "--mode", "read-only"
      ]
    }
  }
}
```

#### Admin mode (Jenkins administrators)

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp-server",
      "args": [
        "--url", "https://your-jenkins.example.com:8443",
        "--username", "admin-username",
        "--token", "admin-api-token",
        "--no-verify-ssl",
        "--mode", "admin"
      ]
    }
  }
}
```

#### Using Environment Variables

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "jenkins-mcp-server",
      "args": ["--no-verify-ssl"],
      "env": {
        "JENKINS_URL": "https://your-jenkins.example.com:8443",
        "JENKINS_USERNAME": "your-username",
        "JENKINS_TOKEN": "your-api-token",
        "JENKINS_MODE": "standard"
      }
    }
  }
}
```

#### Workspace-specific Configuration

Create `.cursor/mcp.json` in your project root with the same format above.

After configuration, restart Cursor or reload MCP servers (**Cmd/Ctrl+Shift+P** → "MCP: Reload Servers").

## MCP Tools Reference

### Jobs & Builds (read-only)

| Tool | Description | Mode |
|------|-------------|------|
| `list_jobs` | List all jobs with status, URLs, and last build info | read-only |
| `get_job_details` | Get detailed job information including builds, health reports | read-only |
| `get_build_info` | Get build status, duration, result, and actions | read-only |
| `get_build_console` | Get console output with line pagination | read-only |
| `get_progressive_console` | Stream console output for live builds (byte offset) | read-only |
| `get_test_report` | Get test pass/fail counts, suites, and cases | read-only |
| `get_coverage_report` | Get code coverage report (requires coverage plugin) | read-only |
| `get_build_parameters` | Get parameters used for a build | read-only |
| `get_artifacts` | List build artifacts | read-only |
| `get_pipeline_stages` | Get Pipeline stage breakdown with status and duration | read-only |
| `get_job_config` | Get raw XML configuration of a job | read-only |

### Infrastructure (read-only)

| Tool | Description | Mode |
|------|-------------|------|
| `get_queue_info` | Get build queue information | read-only |
| `get_queue_item` | Get details about a specific queue item | read-only |
| `list_nodes` | List all Jenkins nodes/agents with status | read-only |
| `get_node_info` | Get specific node details | read-only |
| `list_views` | List all configured views | read-only |
| `get_view_info` | Get view details including contained jobs | read-only |
| `list_credentials` | List credential IDs (values never exposed) | read-only |
| `get_system_info` | Get Jenkins version, executor count, mode | read-only |
| `list_plugins` | List installed plugins with versions | read-only |

### Build Control (standard)

| Tool | Description | Mode |
|------|-------------|------|
| `trigger_build` | Trigger a new build with optional parameters | standard |
| `stop_build` | Stop a running build | standard |

### Administration (admin)

| Tool | Description | Mode |
|------|-------------|------|
| `create_job` | Create a job from XML config or built-in template | admin |
| `delete_job` | Delete a job permanently | admin |
| `enable_job` | Enable a disabled job | admin |
| `disable_job` | Disable a job (prevents new builds) | admin |
| `copy_job` | Copy an existing job to create a new one | admin |
| `update_job_config` | Update a job's XML configuration | admin |
| `create_folder` | Create a folder for organizing jobs | admin |
| `replay_build` | Replay a Pipeline build with optional modified script | admin |

### Job Templates (used with `create_job`)

When using `create_job` without providing raw XML, you can use a built-in template:

| Template | Description |
|----------|-------------|
| `freestyle` | Basic freestyle project with shell build step |
| `pipeline` | Pipeline job with inline Groovy script |
| `pipeline-scm` | Pipeline job loading Jenkinsfile from Git SCM |
| `multibranch` | Multibranch Pipeline scanning branches for Jenkinsfile |

## CLI Reference

```bash
# --- Read commands ---
jenkins-mcp list-jobs                                    # List all jobs
jenkins-mcp list-jobs -f simple                          # Simple format
jenkins-mcp list-jobs --folder MyFolder                  # Jobs in a folder
jenkins-mcp get-job MyJob                                # Job details
jenkins-mcp get-build --job MyJob --build 64             # Build info
jenkins-mcp get-console --job MyJob --build 64 --tail 50 # Console output
jenkins-mcp get-test-report --job MyJob --build 64 -s    # Test summary
jenkins-mcp get-coverage --job MyJob --build 64          # Coverage report
jenkins-mcp get-stages --job MyJob --build 64            # Pipeline stages
jenkins-mcp get-config MyJob                             # Job XML config
jenkins-mcp system-info                                  # Jenkins system info
jenkins-mcp list-plugins                                 # Installed plugins
jenkins-mcp list-views                                   # All views
jenkins-mcp list-credentials                             # Credential IDs
jenkins-mcp list-nodes                                   # Nodes/agents
jenkins-mcp get-queue                                    # Build queue

# --- Build control ---
jenkins-mcp trigger-build MyJob                          # Trigger build
jenkins-mcp trigger-build MyJob -p '{"BRANCH":"main"}'   # With parameters
jenkins-mcp stop-build --job MyJob --build 123           # Stop build

# --- Admin commands ---
jenkins-mcp create-job NewJob --template pipeline --script 'pipeline { agent any { stages { stage("Build") { steps { echo "hi" } } } } }'
jenkins-mcp create-job NewJob --config-file config.xml   # From XML file
jenkins-mcp create-job NewJob --template pipeline-scm --repo-url https://github.com/user/repo.git
jenkins-mcp delete-job OldJob -y                         # Delete (skip confirm)
jenkins-mcp enable-job MyJob                             # Enable
jenkins-mcp disable-job MyJob                            # Disable
jenkins-mcp copy-job SourceJob NewCopy                   # Copy job
jenkins-mcp update-config MyJob new-config.xml           # Update config
jenkins-mcp create-folder MyFolder                       # Create folder
jenkins-mcp replay-build --job MyJob --build 64          # Replay pipeline
```

## Example Prompts for Cursor

Once configured, you can ask Cursor things like:

**Monitoring:**
- "List all Jenkins jobs and their status"
- "Show me the pipeline stages for MyJob build 64"
- "What plugins are installed on Jenkins?"
- "Get the system info for our Jenkins instance"

**Debugging:**
- "Get the test report for MyJob build 64 -- what failed?"
- "Show me the last 100 lines of console output for MyJob build 64"
- "What parameters were used for build 64?"
- "Get the coverage report for the latest build"

**Build control:**
- "Trigger a new build for MyJob with BRANCH=feature-x"
- "Stop build 123 of MyJob"

**Administration (admin mode):**
- "Create a new pipeline job called 'deploy-staging' with this Groovy script: ..."
- "Copy the 'nightly-tests' job to 'nightly-tests-v2'"
- "Disable the 'old-job' job"
- "Create a folder called 'team-alpha' for organizing jobs"

## Python API

```python
from jenkins_mcp_server import JenkinsClient

client = JenkinsClient(
    url="https://your-jenkins.example.com:8443",
    username="your-username",
    token="your-api-token",
    verify_ssl=False,
)

# List jobs
jobs = client.list_jobs()
for job in jobs:
    print(f"{job['name']}: {job.get('color', 'unknown')}")

# Build info
build = client.get_build_info("MyJob", 64)
print(f"Result: {build.get('result')}, Duration: {build.get('duration')}ms")

# Pipeline stages
stages = client.get_pipeline_stages("MyPipeline", 10)
for stage in stages.get('stages', []):
    print(f"  {stage['name']}: {stage['status']}")

# System info
info = client.get_system_info()
print(f"Jenkins {info['version']}, {info['numExecutors']} executors")

# Trigger a build
result = client.trigger_build("MyJob", {"BRANCH": "main"})
print(f"Queued: {result['queue_url']}")

# Create a job from template
from jenkins_mcp_server.client import render_job_template

config = render_job_template("pipeline", script="pipeline { agent any { stages { stage('Build') { steps { echo 'hello' } } } } }")
client.create_job("my-new-pipeline", config)
```

## Troubleshooting

### MCP Server Not Loading in Cursor

1. Verify installation: `pip show jenkins-mcp-tools`
2. Test connection: `jenkins-mcp-server --test --url URL --username USER --token TOKEN --no-verify-ssl`
3. Check Cursor's Output panel for MCP errors
4. Restart Cursor after changing `mcp.json`

### SSL Certificate Errors

Use `--no-verify-ssl` flag or set `JENKINS_VERIFY_SSL=false`.

### Authentication Errors (401)

1. Verify username and token are correct
2. Ensure the API token hasn't been revoked
3. Check if your account has API access permissions
4. Regenerate the token from Jenkins (User → Configure → API Token)

### Mode-related Errors

If you see *"Tool 'X' requires 'admin' mode but server is running in 'standard' mode"*:
- Restart the server with `--mode admin` to enable admin tools
- Or set `JENKINS_MODE=admin` in your environment / Cursor config

### Connection Timeouts

1. Ensure VPN is connected (if required)
2. Test: `curl -I https://your-jenkins.example.com:8443`

## Changelog

### v2.0.0

- **Access modes**: `read-only`, `standard`, `admin` with `--mode` flag and `JENKINS_MODE` env var
- **15 new MCP tools**: pipeline stages, job config, credentials, views, system info, plugins, job CRUD, folder management, build replay
- **Job templates**: Create freestyle, pipeline, pipeline-scm, and multibranch jobs from built-in templates
- **CLI expansion**: New commands for all new tools
- **Sharing guide**: Documentation for distributing to teammates

### v1.0.0

- Initial release with 12 MCP tools
- CLI tool with subcommands
- Cursor IDE integration

## Contributing

1. Clone the repository
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest tests/`
4. Create a feature branch and merge request

## License

MIT License - See LICENSE file for details.

## Support

For issues or questions, open an issue on the repository.
