"""
Main data scraper that orchestrates fetching issues from Jira.
"""
import logging
import time
from typing import Dict, List, Iterator, Optional
from tqdm import tqdm
from scraper.jira_client import JiraClient
from utils.state_manager import StateManager
import config

logger = logging.getLogger(__name__)


class DataScraper:
    """Main scraper for fetching Jira issues."""
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize data scraper.
        
        Args:
            state_manager: State manager for resume capability
        """
        self.client = JiraClient()
        self.state_manager = state_manager
        self.scraped_count = 0
    
    def scrape_project(self, project_key: str) -> Iterator[Dict]:
        """
        Scrape all issues from a project.
        
        Args:
            project_key: Jira project key
            
        Yields:
            Issue dictionaries with full details
        """
        logger.info(f"Starting to scrape project: {project_key}")
        
        # Check if project is already completed
        if self.state_manager.is_project_completed(project_key):
            logger.info(f"Project {project_key} already completed. Skipping.")
            return
        
        self.state_manager.set_current_project(project_key)
        scraped_issues = self.state_manager.get_scraped_issues(project_key)
        
        start_at = 0
        max_results = config.ISSUES_PER_PAGE
        total_issues = None
        
        # Progress bar will be updated as we discover total
        pbar = None
        
        while True:
            try:
                # Fetch issues page
                response = self.client.get_project_issues(
                    project_key,
                    start_at=start_at,
                    max_results=max_results
                )
                
                issues = response.get("issues", [])
                total_issues = response.get("total", 0)
                
                # Initialize progress bar on first iteration
                if pbar is None:
                    pbar = tqdm(
                        total=total_issues,
                        desc=f"Scraping {project_key}",
                        unit="issues"
                    )
                
                if not issues:
                    logger.info(f"No more issues found for {project_key}")
                    break
                
                # Process each issue
                for issue in issues:
                    issue_key = issue.get("key")
                    
                    # Skip if already scraped
                    if issue_key in scraped_issues:
                        pbar.update(1)
                        continue
                    
                    # Fetch full issue details including comments
                    full_issue = self._enrich_issue(issue_key, issue)
                    
                    if full_issue:
                        # Mark as scraped
                        self.state_manager.mark_issue_scraped(project_key, issue_key)
                        self.scraped_count += 1
                        pbar.update(1)
                        
                        yield full_issue
                    else:
                        logger.warning(f"Failed to enrich issue {issue_key}")
                        pbar.update(1)
                
                # Check if we've reached the end
                start_at = response.get("startAt", 0) + len(issues)
                if start_at >= total_issues or len(issues) == 0:
                    break
                
                # Safety limit check
                if self.scraped_count >= config.MAX_ISSUES_PER_PROJECT:
                    logger.warning(
                        f"Reached safety limit of {config.MAX_ISSUES_PER_PROJECT} issues "
                        f"for project {project_key}"
                    )
                    break
                
                # Small delay to be respectful and reduce connection pressure
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"Error scraping project {project_key} at start_at={start_at}: {e}")
                # Save state before continuing
                self.state_manager.save_state()
                # Wait a bit before retrying
                time.sleep(5)
                continue
        
        if pbar:
            pbar.close()
        
        # Mark project as completed
        self.state_manager.mark_project_completed(project_key)
        logger.info(f"Completed scraping project: {project_key}")
    
    def _enrich_issue(self, issue_key: str, issue: Dict) -> Optional[Dict]:
        """
        Enrich issue with comments and additional details.
        
        Args:
            issue_key: Jira issue key
            issue: Basic issue dictionary
            
        Returns:
            Enriched issue dictionary or None if failed
        """
        try:
            # Get comments
            comments = self.client.get_issue_comments(issue_key)
            
            # Add comments to issue
            issue["comments"] = comments
            
            # Ensure all required fields are present
            fields = issue.get("fields", {})
            
            # Handle missing or None fields gracefully
            enriched_issue = {
                "key": issue_key,
                "fields": {
                    "summary": fields.get("summary") or "",
                    "description": fields.get("description") or "",
                    "status": self._extract_field(fields, "status", "name"),
                    "priority": self._extract_field(fields, "priority", "name"),
                    "assignee": self._extract_field(fields, "assignee", "displayName"),
                    "reporter": self._extract_field(fields, "reporter", "displayName"),
                    "created": fields.get("created") or "",
                    "updated": fields.get("updated") or "",
                    "resolutiondate": fields.get("resolutiondate") or "",
                    "labels": fields.get("labels") or [],
                    "components": [
                        comp.get("name", "") for comp in (fields.get("components") or [])
                    ],
                    "fixVersions": [
                        ver.get("name", "") for ver in (fields.get("fixVersions") or [])
                    ],
                    "issuetype": self._extract_field(fields, "issuetype", "name"),
                    "project": {
                        "key": self._extract_field(fields, "project", "key"),
                        "name": self._extract_field(fields, "project", "name")
                    },
                    "comments": [
                        {
                            "author": self._extract_field(comment, "author", "displayName"),
                            "body": comment.get("body") or "",
                            "created": comment.get("created") or ""
                        }
                        for comment in comments
                    ]
                }
            }
            
            return enriched_issue
            
        except Exception as e:
            logger.error(f"Failed to enrich issue {issue_key}: {e}")
            return None
    
    def _extract_field(self, obj: Dict, field: str, subfield: Optional[str] = None) -> str:
        """
        Safely extract a field from a dictionary.
        
        Args:
            obj: Dictionary to extract from
            field: Field name
            subfield: Optional nested field name
            
        Returns:
            Extracted value or empty string
        """
        try:
            value = obj.get(field)
            if value is None:
                return ""
            if subfield and isinstance(value, dict):
                return value.get(subfield, "")
            return str(value) if value else ""
        except Exception:
            return ""
    
    def scrape_all_projects(self, project_keys: List[str]) -> Iterator[Dict]:
        """
        Scrape issues from multiple projects.
        
        Args:
            project_keys: List of project keys to scrape
            
        Yields:
            Issue dictionaries
        """
        logger.info(f"Starting to scrape {len(project_keys)} projects")
        
        # Test connection first
        if not self.client.test_connection():
            logger.error("Failed to connect to Jira API. Aborting.")
            return
        
        for project_key in project_keys:
            try:
                yield from self.scrape_project(project_key)
            except Exception as e:
                logger.error(f"Error scraping project {project_key}: {e}")
                # Save state and continue with next project
                self.state_manager.save_state()
                continue
        
        logger.info(f"Completed scraping. Total issues scraped: {self.scraped_count}")

