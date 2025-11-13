"""
Jira API client with rate limiting and error handling.
"""
import logging
import requests
from typing import Dict, List, Optional, Any
from utils.rate_limiter import RateLimiter
from utils.retry import retry_with_backoff
import config

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for interacting with Apache Jira REST API."""
    
    def __init__(
        self,
        base_url: str = config.JIRA_BASE_URL,
        requests_per_second: int = config.REQUESTS_PER_SECOND,
        timeout: int = config.TIMEOUT,
        max_retries: int = config.MAX_RETRIES
    ):
        """
        Initialize Jira client.
        
        Args:
            base_url: Base URL for Jira REST API
            requests_per_second: Rate limit (requests per second)
            timeout: Request timeout in seconds (or tuple for (connect, read))
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url
        # Use tuple timeout: (connect_timeout, read_timeout)
        self.timeout = (config.CONNECT_TIMEOUT, config.READ_TIMEOUT)
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(requests_per_second, period=1.0)
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Jira-Scraper/1.0 (Educational Purpose)'
        })
        # Configure connection pooling for better reliability
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=0  # We handle retries ourselves
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
    
    @retry_with_backoff(max_retries=5, initial_delay=1.0, max_delay=60.0)
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a rate-limited, retry-enabled request to Jira API.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                import time
                time.sleep(retry_after)
                # Retry the request
                response = self.session.get(url, params=params, timeout=self.timeout)
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Resource not found: {url}")
                return {}
            raise
        except requests.exceptions.Timeout as e:
            # Timeout errors - log as warning since they're retryable
            logger.warning(f"Request timeout for {url}: {str(e)[:100]}... (will retry)")
            raise
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
            # Connection errors are common with Jira - log as warning, not error
            logger.warning(f"Connection issue for {url}: {str(e)[:100]}... (will retry)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
    
    def get_project_issues(
        self,
        project_key: str,
        start_at: int = 0,
        max_results: int = 100,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Get issues for a project with pagination.
        
        Args:
            project_key: Jira project key
            start_at: Starting index for pagination
            max_results: Maximum number of results per page
            fields: List of fields to retrieve
            
        Returns:
            Dictionary containing issues and pagination info
        """
        jql = f"project={project_key} ORDER BY created ASC"
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": fields or config.ISSUE_FIELDS
        }
        
        try:
            return self._make_request("search", params=params)
        except Exception as e:
            logger.error(f"Failed to get issues for project {project_key}: {e}")
            return {"issues": [], "total": 0, "startAt": start_at, "maxResults": max_results}
    
    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Get a single issue by key.
        
        Args:
            issue_key: Jira issue key (e.g., SPARK-1234)
            fields: List of fields to retrieve
            
        Returns:
            Issue dictionary or None if not found
        """
        params = {}
        if fields:
            params["fields"] = fields
        
        try:
            return self._make_request(f"issue/{issue_key}", params=params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Issue not found: {issue_key}")
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return None
    
    def get_issue_comments(self, issue_key: str) -> List[Dict]:
        """
        Get comments for an issue.
        
        Args:
            issue_key: Jira issue key
            
        Returns:
            List of comment dictionaries
        """
        try:
            response = self._make_request(f"issue/{issue_key}/comment")
            return response.get("comments", [])
        except Exception as e:
            logger.error(f"Failed to get comments for {issue_key}: {e}")
            return []
    
    def test_connection(self) -> bool:
        """
        Test connection to Jira API.
        
        Returns:
            True if connection is successful
        """
        try:
            # Try to get server info
            self._make_request("serverInfo")
            logger.info("Successfully connected to Jira API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Jira API: {e}")
            return False

