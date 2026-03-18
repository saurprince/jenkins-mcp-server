"""
Jenkins MCP CLI

Command-line interface for interacting with Jenkins without running the full MCP server.
Useful for quick queries and scripting.
"""

import argparse
import json
import os
import sys
from typing import Optional

from .client import JenkinsClient, render_job_template


def get_client(args: argparse.Namespace) -> JenkinsClient:
    """Create JenkinsClient from arguments or environment."""
    url = args.url or os.environ.get('JENKINS_URL')
    username = args.username or os.environ.get('JENKINS_USERNAME')
    token = args.token or os.environ.get('JENKINS_TOKEN')
    verify_ssl = not (args.no_verify_ssl or 
                      os.environ.get('JENKINS_VERIFY_SSL', 'true').lower() == 'false')
    
    if not all([url, username, token]):
        missing = []
        if not url:
            missing.append("--url or JENKINS_URL")
        if not username:
            missing.append("--username or JENKINS_USERNAME")
        if not token:
            missing.append("--token or JENKINS_TOKEN")
        print(f"Error: Missing {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    
    return JenkinsClient(url, username, token, verify_ssl)


def format_output(data, format_type: str = 'json'):
    """Format output based on requested type."""
    if format_type == 'json':
        return json.dumps(data, indent=2)
    elif format_type == 'table':
        if isinstance(data, list):
            if not data:
                return "No items"
            headers = list(data[0].keys()) if isinstance(data[0], dict) else []
            if headers:
                lines = ['\t'.join(headers)]
                for item in data:
                    lines.append('\t'.join(str(item.get(h, '')) for h in headers))
                return '\n'.join(lines)
        return str(data)
    return str(data)


# ---------------------------------------------------------------------------
# Original commands
# ---------------------------------------------------------------------------

def cmd_list_jobs(args):
    """List all Jenkins jobs."""
    client = get_client(args)
    jobs = client.list_jobs(args.folder)
    
    if args.format == 'simple':
        for job in jobs:
            status = job.get('color', 'unknown')
            last_build = job.get('lastBuild', {})
            build_num = last_build.get('number', 'N/A') if last_build else 'N/A'
            print(f"{job['name']}\t{status}\t#{build_num}")
    else:
        print(format_output(jobs, args.format))


def cmd_get_job(args):
    """Get job details."""
    client = get_client(args)
    job = client.get_job_details(args.job)
    print(format_output(job, args.format))


def cmd_get_build(args):
    """Get build information."""
    client = get_client(args)
    build = client.get_build_info(args.job, args.build)
    print(format_output(build, args.format))


def cmd_get_console(args):
    """Get build console output."""
    client = get_client(args)
    console = client.get_build_console(args.job, args.build)
    
    lines = console.split('\n')
    if args.tail:
        lines = lines[-args.tail:]
    elif args.head:
        lines = lines[:args.head]
    
    print('\n'.join(lines))


def cmd_get_test_report(args):
    """Get test report."""
    client = get_client(args)
    report = client.get_test_report(args.job, args.build)
    
    if args.summary and 'error' not in report:
        print(f"Pass: {report.get('passCount', 0)}")
        print(f"Fail: {report.get('failCount', 0)}")
        print(f"Skip: {report.get('skipCount', 0)}")
        print(f"Duration: {report.get('duration', 0):.2f}s")
    else:
        print(format_output(report, args.format))


def cmd_trigger_build(args):
    """Trigger a new build."""
    client = get_client(args)
    params = json.loads(args.parameters) if args.parameters else None
    result = client.trigger_build(args.job, params)
    print(format_output(result, args.format))


def cmd_stop_build(args):
    """Stop a running build."""
    client = get_client(args)
    result = client.stop_build(args.job, args.build)
    print(format_output(result, args.format))


def cmd_list_nodes(args):
    """List Jenkins nodes."""
    client = get_client(args)
    nodes = client.list_nodes()
    
    if args.format == 'simple':
        for node in nodes:
            name = node.get('displayName', 'unknown')
            offline = 'offline' if node.get('offline', False) else 'online'
            print(f"{name}\t{offline}")
    else:
        print(format_output(nodes, args.format))


def cmd_get_queue(args):
    """Get build queue."""
    client = get_client(args)
    queue = client.get_queue_info()
    print(format_output(queue, args.format))


# ---------------------------------------------------------------------------
# New commands (v2.0)
# ---------------------------------------------------------------------------

def cmd_get_coverage(args):
    """Get coverage report."""
    client = get_client(args)
    report = client.get_coverage_report(args.job, args.build)
    print(format_output(report, args.format))


def cmd_get_stages(args):
    """Get pipeline stages."""
    client = get_client(args)
    stages = client.get_pipeline_stages(args.job, args.build)
    if args.format == 'simple' and 'stages' in stages:
        for s in stages['stages']:
            print(f"{s.get('name', '?')}\t{s.get('status', '?')}\t{s.get('durationMillis', 0)}ms")
    else:
        print(format_output(stages, args.format))


def cmd_get_config(args):
    """Get job XML configuration."""
    client = get_client(args)
    config = client.get_job_config(args.job)
    print(config)


def cmd_update_config(args):
    """Update job XML configuration."""
    client = get_client(args)
    if args.file == '-':
        config_xml = sys.stdin.read()
    else:
        with open(args.file, 'r', encoding='utf-8') as f:
            config_xml = f.read()
    result = client.update_job_config(args.job, config_xml)
    print(format_output(result, args.format))


def cmd_system_info(args):
    """Get Jenkins system info."""
    client = get_client(args)
    info = client.get_system_info()
    if args.format == 'simple':
        print(f"Version: {info.get('version', '?')}")
        print(f"Mode: {info.get('mode', '?')}")
        print(f"Executors: {info.get('numExecutors', '?')}")
        print(f"Quieting Down: {info.get('quietingDown', '?')}")
    else:
        print(format_output(info, args.format))


def cmd_list_plugins(args):
    """List installed plugins."""
    client = get_client(args)
    plugins = client.list_plugins()
    if args.format == 'simple':
        for p in plugins:
            active = 'active' if p.get('active') else 'inactive'
            print(f"{p.get('shortName', '?')}\t{p.get('version', '?')}\t{active}")
    else:
        print(format_output(plugins, args.format))


def cmd_list_views(args):
    """List Jenkins views."""
    client = get_client(args)
    views = client.list_views()
    if args.format == 'simple':
        for v in views:
            print(f"{v.get('name', '?')}\t{v.get('url', '')}")
    else:
        print(format_output(views, args.format))


def cmd_list_credentials(args):
    """List credentials."""
    client = get_client(args)
    creds = client.list_credentials(domain=args.domain)
    print(format_output(creds, args.format))


def cmd_create_job(args):
    """Create a new Jenkins job."""
    client = get_client(args)
    if args.config_file:
        with open(args.config_file, 'r', encoding='utf-8') as f:
            config_xml = f.read()
    else:
        config_xml = render_job_template(
            template=args.template or 'freestyle',
            description=args.description or '',
            script=args.script or '',
            repo_url=args.repo_url or '',
            branch=args.branch or '*/main',
            script_path=args.script_path or 'Jenkinsfile',
            credential_id=args.credential_id or '',
        )
    result = client.create_job(args.job, config_xml, folder=args.folder)
    print(format_output(result, args.format))


def cmd_delete_job(args):
    """Delete a Jenkins job."""
    client = get_client(args)
    if not args.yes:
        confirm = input(f"Delete job '{args.job}'? [y/N] ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return
    result = client.delete_job(args.job)
    print(format_output(result, args.format))


def cmd_enable_job(args):
    """Enable a Jenkins job."""
    client = get_client(args)
    result = client.enable_job(args.job)
    print(format_output(result, args.format))


def cmd_disable_job(args):
    """Disable a Jenkins job."""
    client = get_client(args)
    result = client.disable_job(args.job)
    print(format_output(result, args.format))


def cmd_copy_job(args):
    """Copy a Jenkins job."""
    client = get_client(args)
    result = client.copy_job(args.source, args.new_name)
    print(format_output(result, args.format))


def cmd_create_folder(args):
    """Create a Jenkins folder."""
    client = get_client(args)
    result = client.create_folder(args.name, parent=args.parent)
    print(format_output(result, args.format))


def cmd_replay_build(args):
    """Replay a pipeline build."""
    client = get_client(args)
    script = None
    if args.script_file:
        with open(args.script_file, 'r', encoding='utf-8') as f:
            script = f.read()
    result = client.replay_build(args.job, args.build, script=script)
    print(format_output(result, args.format))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Jenkins CLI - Command line interface for Jenkins',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global arguments
    parser.add_argument('--url', help='Jenkins URL (or JENKINS_URL env)')
    parser.add_argument('--username', '-u', help='Jenkins username (or JENKINS_USERNAME env)')
    parser.add_argument('--token', '-t', help='Jenkins API token (or JENKINS_TOKEN env)')
    parser.add_argument('--no-verify-ssl', '-k', action='store_true', help='Disable SSL verification')
    parser.add_argument('--format', '-f', choices=['json', 'simple', 'table'], default='json',
                        help='Output format (default: json)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # --- Read commands ---------------------------------------------------

    p_list = subparsers.add_parser('list-jobs', aliases=['ls'], help='List all jobs')
    p_list.add_argument('--folder', help='Folder path to list jobs from')
    p_list.set_defaults(func=cmd_list_jobs)
    
    p_job = subparsers.add_parser('get-job', aliases=['job'], help='Get job details')
    p_job.add_argument('job', help='Job name')
    p_job.set_defaults(func=cmd_get_job)
    
    p_build = subparsers.add_parser('get-build', aliases=['build'], help='Get build info')
    p_build.add_argument('--job', '-j', required=True, help='Job name')
    p_build.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_build.set_defaults(func=cmd_get_build)
    
    p_console = subparsers.add_parser('get-console', aliases=['console', 'log'], help='Get build console')
    p_console.add_argument('--job', '-j', required=True, help='Job name')
    p_console.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_console.add_argument('--tail', type=int, help='Show last N lines')
    p_console.add_argument('--head', type=int, help='Show first N lines')
    p_console.set_defaults(func=cmd_get_console)
    
    p_test = subparsers.add_parser('get-test-report', aliases=['test', 'tests'], help='Get test report')
    p_test.add_argument('--job', '-j', required=True, help='Job name')
    p_test.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_test.add_argument('--summary', '-s', action='store_true', help='Show summary only')
    p_test.set_defaults(func=cmd_get_test_report)

    p_coverage = subparsers.add_parser('get-coverage', aliases=['coverage'], help='Get coverage report')
    p_coverage.add_argument('--job', '-j', required=True, help='Job name')
    p_coverage.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_coverage.set_defaults(func=cmd_get_coverage)

    p_stages = subparsers.add_parser('get-stages', aliases=['stages'], help='Get pipeline stages')
    p_stages.add_argument('--job', '-j', required=True, help='Job name')
    p_stages.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_stages.set_defaults(func=cmd_get_stages)

    p_config = subparsers.add_parser('get-config', aliases=['config'], help='Get job XML config')
    p_config.add_argument('job', help='Job name')
    p_config.set_defaults(func=cmd_get_config)

    p_sysinfo = subparsers.add_parser('system-info', aliases=['sysinfo'], help='Jenkins system info')
    p_sysinfo.set_defaults(func=cmd_system_info)

    p_plugins = subparsers.add_parser('list-plugins', aliases=['plugins'], help='List installed plugins')
    p_plugins.set_defaults(func=cmd_list_plugins)

    p_views = subparsers.add_parser('list-views', aliases=['views'], help='List Jenkins views')
    p_views.set_defaults(func=cmd_list_views)

    p_creds = subparsers.add_parser('list-credentials', aliases=['creds'], help='List credentials')
    p_creds.add_argument('--domain', default='_', help='Credential domain (default: _)')
    p_creds.set_defaults(func=cmd_list_credentials)

    p_nodes = subparsers.add_parser('list-nodes', aliases=['nodes'], help='List Jenkins nodes')
    p_nodes.set_defaults(func=cmd_list_nodes)
    
    p_queue = subparsers.add_parser('get-queue', aliases=['queue'], help='Get build queue')
    p_queue.set_defaults(func=cmd_get_queue)

    # --- Write commands --------------------------------------------------

    p_trigger = subparsers.add_parser('trigger-build', aliases=['trigger', 'run'], help='Trigger a build')
    p_trigger.add_argument('job', help='Job name')
    p_trigger.add_argument('--parameters', '-p', help='Build parameters as JSON')
    p_trigger.set_defaults(func=cmd_trigger_build)
    
    p_stop = subparsers.add_parser('stop-build', aliases=['stop', 'abort'], help='Stop a build')
    p_stop.add_argument('--job', '-j', required=True, help='Job name')
    p_stop.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_stop.set_defaults(func=cmd_stop_build)

    # --- Admin commands --------------------------------------------------

    p_create = subparsers.add_parser('create-job', help='Create a new job')
    p_create.add_argument('job', help='Job name')
    p_create.add_argument('--config-file', help='Path to config.xml file')
    p_create.add_argument('--template', choices=['freestyle', 'pipeline', 'pipeline-scm', 'multibranch'],
                          help='Built-in template')
    p_create.add_argument('--description', help='Job description')
    p_create.add_argument('--script', help='Shell or Groovy script')
    p_create.add_argument('--repo-url', help='Git repo URL (pipeline-scm)')
    p_create.add_argument('--branch', default='*/main', help='Branch (pipeline-scm)')
    p_create.add_argument('--script-path', default='Jenkinsfile', help='Jenkinsfile path')
    p_create.add_argument('--credential-id', help='Jenkins credential ID')
    p_create.add_argument('--folder', help='Parent folder')
    p_create.set_defaults(func=cmd_create_job)

    p_delete = subparsers.add_parser('delete-job', help='Delete a job')
    p_delete.add_argument('job', help='Job name')
    p_delete.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')
    p_delete.set_defaults(func=cmd_delete_job)

    p_enable = subparsers.add_parser('enable-job', help='Enable a job')
    p_enable.add_argument('job', help='Job name')
    p_enable.set_defaults(func=cmd_enable_job)

    p_disable = subparsers.add_parser('disable-job', help='Disable a job')
    p_disable.add_argument('job', help='Job name')
    p_disable.set_defaults(func=cmd_disable_job)

    p_copy = subparsers.add_parser('copy-job', aliases=['copy'], help='Copy a job')
    p_copy.add_argument('source', help='Source job name')
    p_copy.add_argument('new_name', help='New job name')
    p_copy.set_defaults(func=cmd_copy_job)

    p_upconfig = subparsers.add_parser('update-config', help='Update job XML config')
    p_upconfig.add_argument('job', help='Job name')
    p_upconfig.add_argument('file', help='Path to new config.xml (use - for stdin)')
    p_upconfig.set_defaults(func=cmd_update_config)

    p_folder = subparsers.add_parser('create-folder', help='Create a folder')
    p_folder.add_argument('name', help='Folder name')
    p_folder.add_argument('--parent', help='Parent folder')
    p_folder.set_defaults(func=cmd_create_folder)

    p_replay = subparsers.add_parser('replay-build', aliases=['replay'], help='Replay a pipeline build')
    p_replay.add_argument('--job', '-j', required=True, help='Job name')
    p_replay.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_replay.add_argument('--script-file', help='Modified pipeline script file')
    p_replay.set_defaults(func=cmd_replay_build)

    # --- Parse and run ---------------------------------------------------
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
