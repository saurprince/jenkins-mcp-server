"""
Jenkins API Client

Provides a clean interface for interacting with Jenkins REST API.
"""

import logging
import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

JOB_TEMPLATES: Dict[str, str] = {
    "freestyle": (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<project>'
        '<actions/><description>{description}</description>'
        '<keepDependencies>false</keepDependencies><properties/>'
        '<scm class="hudson.scm.NullSCM"/>'
        '<canRoam>true</canRoam><disabled>false</disabled>'
        '<blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>'
        '<blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>'
        '<triggers/><concurrentBuild>false</concurrentBuild>'
        '<builders>'
        '<hudson.tasks.Shell><command>{script}</command></hudson.tasks.Shell>'
        '</builders><publishers/><buildWrappers/>'
        '</project>'
    ),
    "pipeline": (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<flow-definition plugin="workflow-job">'
        '<actions/><description>{description}</description>'
        '<keepDependencies>false</keepDependencies><properties/>'
        '<definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">'
        '<script>{script}</script><sandbox>true</sandbox>'
        '</definition><triggers/><disabled>false</disabled>'
        '</flow-definition>'
    ),
    "pipeline-scm": (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<flow-definition plugin="workflow-job">'
        '<actions/><description>{description}</description>'
        '<keepDependencies>false</keepDependencies><properties/>'
        '<definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition" plugin="workflow-cps">'
        '<scm class="hudson.plugins.git.GitSCM" plugin="git">'
        '<configVersion>2</configVersion>'
        '<userRemoteConfigs><hudson.plugins.git.UserRemoteConfig>'
        '<url>{repo_url}</url>{credential_xml}'
        '</hudson.plugins.git.UserRemoteConfig></userRemoteConfigs>'
        '<branches><hudson.plugins.git.BranchSpec><name>{branch}</name></hudson.plugins.git.BranchSpec></branches>'
        '</scm><scriptPath>{script_path}</scriptPath><lightweight>true</lightweight>'
        '</definition><triggers/><disabled>false</disabled>'
        '</flow-definition>'
    ),
    "multibranch": (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject plugin="workflow-multibranch">'
        '<actions/><description>{description}</description><properties/>'
        '<folderViews class="jenkins.branch.MultiBranchProjectViewHolder" plugin="branch-api"/>'
        '<healthMetrics/>'
        '<factory class="org.jenkinsci.plugins.workflow.multibranch.WorkflowBranchProjectFactory">'
        '<owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>'
        '<scriptPath>{script_path}</scriptPath>'
        '</factory>'
        '</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>'
    ),
}


def render_job_template(
    template: str,
    description: str = "",
    script: str = "",
    repo_url: str = "",
    branch: str = "*/main",
    script_path: str = "Jenkinsfile",
    credential_id: str = "",
) -> str:
    """Render a job template with the given parameters.

    Args:
        template: Template key from JOB_TEMPLATES
        description: Job description
        script: Inline script (freestyle shell or pipeline Groovy)
        repo_url: Git repository URL (for pipeline-scm)
        branch: Branch specifier (for pipeline-scm)
        script_path: Path to Jenkinsfile (for pipeline-scm and multibranch)
        credential_id: Jenkins credential ID for SCM access

    Returns:
        Rendered XML configuration string

    Raises:
        ValueError: If template key is unknown
    """
    if template not in JOB_TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Available: {', '.join(JOB_TEMPLATES)}")
    credential_xml = (
        f"<credentialsId>{credential_id}</credentialsId>" if credential_id else ""
    )
    return JOB_TEMPLATES[template].format(
        description=description,
        script=script,
        repo_url=repo_url,
        branch=branch,
        script_path=script_path,
        credential_xml=credential_xml,
    )


class JenkinsClient:
    """Jenkins API client for interacting with Jenkins server.
    
    Args:
        url: Jenkins server URL (e.g., https://jenkins.example.com:8443)
        username: Jenkins username
        token: Jenkins API token (preferred) or password
        verify_ssl: Whether to verify SSL certificates (default: True)
    
    Example:
        >>> client = JenkinsClient(
        ...     url="https://jenkins.example.com:8443",
        ...     username="user",
        ...     token="api-token",
        ...     verify_ssl=False
        ... )
        >>> jobs = client.list_jobs()
        >>> print(f"Found {len(jobs)} jobs")
    """
    
    def __init__(
        self,
        url: str,
        username: str,
        token: str,
        verify_ssl: bool = True
    ):
        """Initialize Jenkins client."""
        self.url = url.rstrip('/')
        self.username = username
        self.token = token
        self.verify_ssl = verify_ssl
        self.auth = HTTPBasicAuth(username, token)
        
        # Configure session
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = verify_ssl
        
        # Suppress SSL warnings if verification is disabled
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 30
    ) -> requests.Response:
        """Make HTTP request to Jenkins API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (will be appended to base URL)
            params: Query parameters
            data: Form data
            json_data: JSON data
            timeout: Request timeout in seconds
            
        Returns:
            Response object
            
        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.url}{path}"
        logger.debug(f"Making {method} request to {url}")
        
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json_data,
            timeout=timeout
        )
        
        return response
    
    def get_api_json(
        self,
        path: str = "",
        tree: Optional[str] = None,
        depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get JSON data from Jenkins API.
        
        Args:
            path: Base path (without /api/json)
            tree: Tree parameter to filter response fields
            depth: Depth parameter for nested data
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.HTTPError: If request fails
        """
        api_path = f"{path}/api/json"
        params = {}
        if tree:
            params['tree'] = tree
        if depth is not None:
            params['depth'] = depth
            
        response = self._request('GET', api_path, params=params)
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self, folder: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all Jenkins jobs.
        
        Args:
            folder: Optional folder path to list jobs from
            
        Returns:
            List of job dictionaries with name, url, color (status), lastBuild
        """
        path = f"/job/{urllib.parse.quote(folder, safe='')}" if folder else ""
        data = self.get_api_json(
            path,
            tree='jobs[name,url,color,lastBuild[number,result,timestamp,duration]]'
        )
        return data.get('jobs', [])
    
    def get_job_details(self, job_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific job.
        
        Args:
            job_name: Name of the job (can include folder path like "folder/job")
            
        Returns:
            Job details including builds, health reports, configuration
        """
        encoded_name = self._encode_job_path(job_name)
        return self.get_api_json(f"/job/{encoded_name}")
    
    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get information about a specific build.
        
        Args:
            job_name: Name of the job
            build_number: Build number
            
        Returns:
            Build information including status, duration, result, actions
        """
        encoded_name = self._encode_job_path(job_name)
        return self.get_api_json(f"/job/{encoded_name}/{build_number}")
    
    def get_build_console(self, job_name: str, build_number: int) -> str:
        """Get console output from a build.
        
        Args:
            job_name: Name of the job
            build_number: Build number
            
        Returns:
            Console output as string
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request('GET', f"/job/{encoded_name}/{build_number}/consoleText")
        response.raise_for_status()
        return response.text
    
    def get_progressive_console(
        self,
        job_name: str,
        build_number: int,
        start: int = 0
    ) -> Dict[str, Any]:
        """Get progressive console output (for following live builds).
        
        Args:
            job_name: Name of the job
            build_number: Build number
            start: Byte offset to start from
            
        Returns:
            Dictionary with 'text', 'size', and 'hasMoreData'
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request(
            'GET',
            f"/job/{encoded_name}/{build_number}/logText/progressiveText",
            params={'start': start}
        )
        response.raise_for_status()
        
        return {
            'text': response.text,
            'size': int(response.headers.get('X-Text-Size', len(response.text))),
            'hasMoreData': response.headers.get('X-More-Data', 'false').lower() == 'true'
        }
    
    def trigger_build(
        self,
        job_name: str,
        parameters: Optional[Dict[str, str]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a new build for a job.
        
        Args:
            job_name: Name of the job
            parameters: Build parameters (optional)
            token: Build token for remote triggering (optional)
            
        Returns:
            Queue item information with queue_url
        """
        encoded_name = self._encode_job_path(job_name)
        
        params = {}
        if token:
            params['token'] = token
        if parameters:
            params.update(parameters)
        
        path = f"/job/{encoded_name}/buildWithParameters" if parameters else f"/job/{encoded_name}/build"
        response = self._request('POST', path, params=params if params else None)
        response.raise_for_status()
        
        queue_url = response.headers.get('Location', '')
        return {
            'queued': True,
            'queue_url': queue_url,
            'message': f"Build triggered for {job_name}"
        }
    
    def stop_build(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Stop a running build.
        
        Args:
            job_name: Name of the job
            build_number: Build number to stop
            
        Returns:
            Status message
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request('POST', f"/job/{encoded_name}/{build_number}/stop")
        response.raise_for_status()
        return {'message': f"Stop requested for {job_name} #{build_number}"}
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get information about the Jenkins build queue.
        
        Returns:
            Queue information including pending builds
        """
        return self.get_api_json('/queue')
    
    def get_queue_item(self, queue_id: int) -> Dict[str, Any]:
        """Get information about a specific queue item.
        
        Args:
            queue_id: Queue item ID
            
        Returns:
            Queue item details
        """
        return self.get_api_json(f'/queue/item/{queue_id}')
    
    def list_nodes(self) -> List[Dict[str, Any]]:
        """List all Jenkins nodes/agents.
        
        Returns:
            List of node dictionaries with status and configuration
        """
        data = self.get_api_json('/computer')
        return data.get('computer', [])
    
    def get_node_info(self, node_name: str) -> Dict[str, Any]:
        """Get information about a specific node.
        
        Args:
            node_name: Name of the node (use "(master)" or "(built-in)" for built-in node)
            
        Returns:
            Node information including status, executors, labels
        """
        encoded_name = urllib.parse.quote(node_name, safe='')
        return self.get_api_json(f"/computer/{encoded_name}")
    
    def get_test_report(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get test report for a build.
        
        Args:
            job_name: Name of the job
            build_number: Build number
            
        Returns:
            Test report data including pass/fail counts, suites, cases
            
        Note:
            Returns {'error': 'No test report available'} if no test report exists
        """
        encoded_name = self._encode_job_path(job_name)
        try:
            return self.get_api_json(f"/job/{encoded_name}/{build_number}/testReport")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return {'error': 'No test report available for this build'}
            raise
    
    def get_coverage_report(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get code coverage report for a build (if available).
        
        Args:
            job_name: Name of the job
            build_number: Build number
            
        Returns:
            Coverage report data or error message
        """
        encoded_name = self._encode_job_path(job_name)
        try:
            return self.get_api_json(f"/job/{encoded_name}/{build_number}/coverage/result")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return {'error': 'No coverage report available for this build'}
            raise
    
    def get_artifacts(self, job_name: str, build_number: int) -> List[Dict[str, Any]]:
        """Get list of artifacts for a build.
        
        Args:
            job_name: Name of the job
            build_number: Build number
            
        Returns:
            List of artifact dictionaries with name, path, size
        """
        build_info = self.get_build_info(job_name, build_number)
        return build_info.get('artifacts', [])
    
    def get_build_parameters(self, job_name: str, build_number: int) -> List[Dict[str, Any]]:
        """Get parameters used for a build.
        
        Args:
            job_name: Name of the job
            build_number: Build number
            
        Returns:
            List of parameter dictionaries
        """
        build_info = self.get_build_info(job_name, build_number)
        for action in build_info.get('actions', []):
            if action.get('_class') == 'hudson.model.ParametersAction':
                return action.get('parameters', [])
        return []
    
    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def get_pipeline_stages(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get Pipeline stage/step breakdown for a build.

        Uses the Pipeline REST API (wfapi) available on Pipeline jobs.

        Args:
            job_name: Name of the Pipeline job
            build_number: Build number

        Returns:
            Stage descriptions with status, duration, and steps.
            Returns error dict if the job is not a Pipeline or the endpoint is unavailable.
        """
        encoded_name = self._encode_job_path(job_name)
        try:
            response = self._request(
                'GET',
                f"/job/{encoded_name}/{build_number}/wfapi/describe"
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return {'error': 'Pipeline stage info not available (job may not be a Pipeline)'}
            raise

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def get_job_config(self, job_name: str) -> str:
        """Get the raw XML configuration of a job.

        Args:
            job_name: Name of the job

        Returns:
            config.xml content as a string
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request('GET', f"/job/{encoded_name}/config.xml")
        response.raise_for_status()
        return response.text

    def update_job_config(self, job_name: str, config_xml: str) -> Dict[str, Any]:
        """Update a job's XML configuration.

        Args:
            job_name: Name of the job
            config_xml: New config.xml content

        Returns:
            Status message
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request(
            'POST',
            f"/job/{encoded_name}/config.xml",
            data=config_xml.encode('utf-8'),
        )
        response.raise_for_status()
        return {'message': f"Configuration updated for {job_name}"}

    def create_job(
        self,
        job_name: str,
        config_xml: str,
        folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Jenkins job.

        Args:
            job_name: Name for the new job
            config_xml: Job configuration XML
            folder: Optional folder to create the job in

        Returns:
            Status message with job URL
        """
        base = f"/job/{self._encode_job_path(folder)}" if folder else ""
        response = self._request(
            'POST',
            f"{base}/createItem",
            params={'name': job_name},
            data=config_xml.encode('utf-8'),
        )
        response.raise_for_status()
        job_path = f"{folder}/{job_name}" if folder else job_name
        return {'message': f"Job '{job_path}' created", 'url': f"{self.url}/job/{self._encode_job_path(job_path)}"}

    def delete_job(self, job_name: str) -> Dict[str, Any]:
        """Delete a Jenkins job.

        Args:
            job_name: Name of the job to delete

        Returns:
            Status message
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request('POST', f"/job/{encoded_name}/doDelete")
        response.raise_for_status()
        return {'message': f"Job '{job_name}' deleted"}

    def enable_job(self, job_name: str) -> Dict[str, Any]:
        """Enable a disabled Jenkins job.

        Args:
            job_name: Name of the job

        Returns:
            Status message
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request('POST', f"/job/{encoded_name}/enable")
        response.raise_for_status()
        return {'message': f"Job '{job_name}' enabled"}

    def disable_job(self, job_name: str) -> Dict[str, Any]:
        """Disable a Jenkins job.

        Args:
            job_name: Name of the job

        Returns:
            Status message
        """
        encoded_name = self._encode_job_path(job_name)
        response = self._request('POST', f"/job/{encoded_name}/disable")
        response.raise_for_status()
        return {'message': f"Job '{job_name}' disabled"}

    def copy_job(self, source_name: str, new_name: str) -> Dict[str, Any]:
        """Copy an existing job to create a new one.

        Args:
            source_name: Name of the source job
            new_name: Name for the new job

        Returns:
            Status message
        """
        response = self._request(
            'POST',
            '/createItem',
            params={'name': new_name, 'mode': 'copy', 'from': source_name},
        )
        response.raise_for_status()
        return {'message': f"Job '{source_name}' copied to '{new_name}'"}

    # ------------------------------------------------------------------
    # Folder management
    # ------------------------------------------------------------------

    def create_folder(self, folder_name: str, parent: Optional[str] = None) -> Dict[str, Any]:
        """Create a new folder in Jenkins.

        Args:
            folder_name: Name for the new folder
            parent: Optional parent folder path

        Returns:
            Status message
        """
        folder_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder">'
            '<actions/><description></description><properties/>'
            '<views><hudson.model.AllView><name>All</name><filterExecutors>false</filterExecutors>'
            '<filterQueue>false</filterQueue><properties class="hudson.model.View$PropertyList"/>'
            '</hudson.model.AllView></views>'
            '<viewsTabBar class="hudson.views.DefaultViewsTabBar"/>'
            '<healthMetrics/>'
            '</com.cloudbees.hudson.plugins.folder.Folder>'
        )
        base = f"/job/{self._encode_job_path(parent)}" if parent else ""
        response = self._request(
            'POST',
            f"{base}/createItem",
            params={'name': folder_name},
            data=folder_xml.encode('utf-8'),
        )
        response.raise_for_status()
        path = f"{parent}/{folder_name}" if parent else folder_name
        return {'message': f"Folder '{path}' created"}

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def list_credentials(self, domain: str = "_") -> Dict[str, Any]:
        """List credentials in the given domain.

        Args:
            domain: Credential domain (default ``_`` for the global domain)

        Returns:
            Credentials list (keys/IDs only -- values are never exposed by Jenkins)
        """
        encoded_domain = urllib.parse.quote(domain, safe='')
        try:
            return self.get_api_json(
                f"/credentials/store/system/domain/{encoded_domain}",
                depth=1,
            )
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return {'error': 'Credentials API not available (Credentials plugin may not be installed)'}
            raise

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def list_views(self) -> List[Dict[str, Any]]:
        """List all views on the Jenkins instance.

        Returns:
            List of view dicts with name, url, description
        """
        data = self.get_api_json('', tree='views[name,url,description]')
        return data.get('views', [])

    def get_view_info(self, view_name: str) -> Dict[str, Any]:
        """Get detailed information about a view.

        Args:
            view_name: Name of the view

        Returns:
            View details including contained jobs
        """
        encoded = urllib.parse.quote(view_name, safe='')
        return self.get_api_json(f"/view/{encoded}")

    # ------------------------------------------------------------------
    # System information
    # ------------------------------------------------------------------

    def get_system_info(self) -> Dict[str, Any]:
        """Get Jenkins system information.

        Returns:
            Dict with version, mode, node description, executor count, etc.
        """
        data = self.get_api_json(
            '',
            tree='mode,nodeDescription,numExecutors,quietingDown,useSecurity,primaryView[name]',
        )
        head_response = self._request('HEAD', '/api/json')
        data['version'] = head_response.headers.get('X-Jenkins', 'unknown')
        return data

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List installed Jenkins plugins.

        Returns:
            List of plugin dicts with shortName, longName, version, active, enabled
        """
        data = self.get_api_json('/pluginManager', depth=1)
        return data.get('plugins', [])

    # ------------------------------------------------------------------
    # Build replay (Pipeline)
    # ------------------------------------------------------------------

    def replay_build(
        self,
        job_name: str,
        build_number: int,
        script: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Replay a Pipeline build, optionally with a modified script.

        Args:
            job_name: Name of the Pipeline job
            build_number: Build number to replay
            script: Optional modified Groovy pipeline script

        Returns:
            Status message
        """
        encoded_name = self._encode_job_path(job_name)
        data = {}
        if script:
            data['mainScript'] = script
        response = self._request(
            'POST',
            f"/job/{encoded_name}/{build_number}/replay/run",
            data=data if data else None,
        )
        response.raise_for_status()
        return {'message': f"Replay triggered for {job_name} #{build_number}"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _encode_job_path(self, job_name: str) -> str:
        """Encode job path for URL (handles folder/job paths).
        
        Args:
            job_name: Job name, possibly with folder path (e.g., "folder/subfolder/job")
            
        Returns:
            URL-encoded path with /job/ between components
        """
        parts = job_name.split('/')
        encoded_parts = [urllib.parse.quote(part, safe='') for part in parts]
        return '/job/'.join(encoded_parts)
    
    def test_connection(self) -> bool:
        """Test connection to Jenkins server.
        
        Returns:
            True if connection successful
            
        Raises:
            requests.RequestException: If connection fails
        """
        response = self._request('GET', '/api/json', params={'tree': 'mode'})
        response.raise_for_status()
        return True
