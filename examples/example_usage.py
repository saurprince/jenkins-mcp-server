#!/usr/bin/env python3
"""
Example usage of the Jenkins MCP Server client library.

Run this script to see various examples of interacting with Jenkins.
Make sure to set environment variables or modify the credentials below.
"""

import os
from jenkins_mcp_server import JenkinsClient
from jenkins_mcp_server.client import render_job_template


def main():
    url = os.environ.get('JENKINS_URL', 'https://your-jenkins.example.com:8443')
    username = os.environ.get('JENKINS_USERNAME', 'your-username')
    token = os.environ.get('JENKINS_TOKEN', 'your-token')

    client = JenkinsClient(
        url=url,
        username=username,
        token=token,
        verify_ssl=False,
    )

    print("=" * 60)
    print("Jenkins MCP Server v2.0 - Example Usage")
    print("=" * 60)

    # 1. List all jobs
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

    # 2. System info
    print("\n2. Getting Jenkins system info...")
    try:
        info = client.get_system_info()
        print(f"   Version: {info.get('version')}")
        print(f"   Mode: {info.get('mode')}")
        print(f"   Executors: {info.get('numExecutors')}")
    except Exception as e:
        print(f"   Error: {e}")

    # 3. List views
    print("\n3. Listing views...")
    try:
        views = client.list_views()
        print(f"   Found {len(views)} views")
        for v in views[:5]:
            print(f"   - {v.get('name')}: {v.get('url')}")
    except Exception as e:
        print(f"   Error: {e}")

    # 4. List plugins (first 5)
    print("\n4. Listing plugins (first 5)...")
    try:
        plugins = client.list_plugins()
        print(f"   Found {len(plugins)} plugins")
        for p in plugins[:5]:
            print(f"   - {p.get('shortName')} v{p.get('version')} ({'active' if p.get('active') else 'inactive'})")
    except Exception as e:
        print(f"   Error: {e}")

    # 5. List nodes
    print("\n5. Listing Jenkins nodes...")
    try:
        nodes = client.list_nodes()
        print(f"   Found {len(nodes)} nodes")
        for node in nodes[:5]:
            name = node.get('displayName', 'unknown')
            offline = 'offline' if node.get('offline') else 'online'
            print(f"   - {name}: {offline}")
    except Exception as e:
        print(f"   Error: {e}")

    # 6. Get job details
    print("\n6. Getting job details for first job...")
    try:
        jobs = client.list_jobs()
        if jobs:
            job_name = jobs[0]['name']
            job = client.get_job_details(job_name)
            print(f"   Name: {job.get('name')}")
            print(f"   Buildable: {job.get('buildable')}")
            last_build = job.get('lastBuild', {})
            if last_build:
                print(f"   Last build: #{last_build.get('number')}")

                # 7. Pipeline stages (if applicable)
                print(f"\n7. Checking pipeline stages for {job_name} #{last_build.get('number')}...")
                stages = client.get_pipeline_stages(job_name, last_build['number'])
                if 'error' not in stages:
                    for s in stages.get('stages', []):
                        print(f"   - {s.get('name')}: {s.get('status')} ({s.get('durationMillis', 0)}ms)")
                else:
                    print(f"   {stages['error']}")
    except Exception as e:
        print(f"   Error: {e}")

    # 8. Job template rendering (no API call needed)
    print("\n8. Rendering job templates (local only)...")
    for tmpl in ['freestyle', 'pipeline', 'pipeline-scm', 'multibranch']:
        try:
            xml = render_job_template(
                tmpl,
                description=f'Demo {tmpl} job',
                script='echo hello',
                repo_url='https://github.com/example/repo.git',
            )
            print(f"   - {tmpl}: {len(xml)} chars of XML")
        except Exception as e:
            print(f"   - {tmpl}: Error: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
