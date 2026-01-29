#!/usr/bin/env python3
"""
Example usage of the Jenkins MCP Server client library.

Run this script to see various examples of interacting with Jenkins.
Make sure to set environment variables or modify the credentials below.
"""

import os
from jenkins_mcp_server import JenkinsClient


def main():
    # Get credentials from environment or use defaults for demo
    url = os.environ.get('JENKINS_URL', 'https://dcpinternal.druva.org:8443')
    username = os.environ.get('JENKINS_USERNAME', 'your-username')
    token = os.environ.get('JENKINS_TOKEN', 'your-token')
    
    # Create client
    client = JenkinsClient(
        url=url,
        username=username,
        token=token,
        verify_ssl=False  # For self-signed certificates
    )
    
    print("=" * 60)
    print("Jenkins MCP Server - Example Usage")
    print("=" * 60)
    
    # Example 1: List all jobs
    print("\n1. Listing all jobs...")
    try:
        jobs = client.list_jobs()
        print(f"   Found {len(jobs)} jobs")
        for job in jobs[:5]:
            status = job.get('color', 'unknown')
            last_build = job.get('lastBuild', {})
            build_num = last_build.get('number', 'N/A') if last_build else 'N/A'
            print(f"   - {job['name']}: {status} (#{build_num})")
        if len(jobs) > 5:
            print(f"   ... and {len(jobs) - 5} more")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 2: Get job details
    print("\n2. Getting job details for 'Orcas_Nightly'...")
    try:
        job = client.get_job_details('Orcas_Nightly')
        print(f"   Name: {job.get('name')}")
        print(f"   URL: {job.get('url')}")
        print(f"   Buildable: {job.get('buildable')}")
        last_build = job.get('lastBuild', {})
        if last_build:
            print(f"   Last build: #{last_build.get('number')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 3: Get build information
    print("\n3. Getting build info for 'Orcas_Nightly' #64...")
    try:
        build = client.get_build_info('Orcas_Nightly', 64)
        print(f"   Result: {build.get('result')}")
        print(f"   Duration: {build.get('duration', 0) / 1000:.1f} seconds")
        print(f"   Building: {build.get('building')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 4: Get test report
    print("\n4. Getting test report for 'Orcas_Nightly' #64...")
    try:
        report = client.get_test_report('Orcas_Nightly', 64)
        if 'error' in report:
            print(f"   {report['error']}")
        else:
            print(f"   Passed: {report.get('passCount', 0)}")
            print(f"   Failed: {report.get('failCount', 0)}")
            print(f"   Skipped: {report.get('skipCount', 0)}")
            print(f"   Duration: {report.get('duration', 0):.2f} seconds")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 5: Get build parameters
    print("\n5. Getting build parameters for 'Orcas_Nightly' #64...")
    try:
        params = client.get_build_parameters('Orcas_Nightly', 64)
        if params:
            for param in params[:5]:
                print(f"   {param.get('name')}: {param.get('value')}")
        else:
            print("   No parameters found")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 6: List nodes
    print("\n6. Listing Jenkins nodes...")
    try:
        nodes = client.list_nodes()
        print(f"   Found {len(nodes)} nodes")
        for node in nodes[:5]:
            name = node.get('displayName', 'unknown')
            offline = 'offline' if node.get('offline') else 'online'
            print(f"   - {name}: {offline}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 7: Get queue info
    print("\n7. Getting build queue info...")
    try:
        queue = client.get_queue_info()
        items = queue.get('items', [])
        print(f"   {len(items)} items in queue")
        for item in items[:3]:
            task = item.get('task', {})
            print(f"   - {task.get('name', 'unknown')}: {item.get('why', 'waiting')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
