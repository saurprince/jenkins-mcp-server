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

from .client import JenkinsClient


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
        # Simple table format for lists
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
    
    # list-jobs
    p_list = subparsers.add_parser('list-jobs', aliases=['ls'], help='List all jobs')
    p_list.add_argument('--folder', help='Folder path to list jobs from')
    p_list.set_defaults(func=cmd_list_jobs)
    
    # get-job
    p_job = subparsers.add_parser('get-job', aliases=['job'], help='Get job details')
    p_job.add_argument('job', help='Job name')
    p_job.set_defaults(func=cmd_get_job)
    
    # get-build
    p_build = subparsers.add_parser('get-build', aliases=['build'], help='Get build info')
    p_build.add_argument('--job', '-j', required=True, help='Job name')
    p_build.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_build.set_defaults(func=cmd_get_build)
    
    # get-console
    p_console = subparsers.add_parser('get-console', aliases=['console', 'log'], help='Get build console')
    p_console.add_argument('--job', '-j', required=True, help='Job name')
    p_console.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_console.add_argument('--tail', type=int, help='Show last N lines')
    p_console.add_argument('--head', type=int, help='Show first N lines')
    p_console.set_defaults(func=cmd_get_console)
    
    # get-test-report
    p_test = subparsers.add_parser('get-test-report', aliases=['test', 'tests'], help='Get test report')
    p_test.add_argument('--job', '-j', required=True, help='Job name')
    p_test.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_test.add_argument('--summary', '-s', action='store_true', help='Show summary only')
    p_test.set_defaults(func=cmd_get_test_report)
    
    # trigger-build
    p_trigger = subparsers.add_parser('trigger-build', aliases=['trigger', 'run'], help='Trigger a build')
    p_trigger.add_argument('job', help='Job name')
    p_trigger.add_argument('--parameters', '-p', help='Build parameters as JSON')
    p_trigger.set_defaults(func=cmd_trigger_build)
    
    # stop-build
    p_stop = subparsers.add_parser('stop-build', aliases=['stop', 'abort'], help='Stop a build')
    p_stop.add_argument('--job', '-j', required=True, help='Job name')
    p_stop.add_argument('--build', '-b', type=int, required=True, help='Build number')
    p_stop.set_defaults(func=cmd_stop_build)
    
    # list-nodes
    p_nodes = subparsers.add_parser('list-nodes', aliases=['nodes'], help='List Jenkins nodes')
    p_nodes.set_defaults(func=cmd_list_nodes)
    
    # get-queue
    p_queue = subparsers.add_parser('get-queue', aliases=['queue'], help='Get build queue')
    p_queue.set_defaults(func=cmd_get_queue)
    
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
