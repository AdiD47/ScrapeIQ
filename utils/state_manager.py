"""
State management for resuming interrupted scraping sessions.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StateManager:
    """Manages scraping state for resume capability."""
    
    def __init__(self, state_file: Path):
        """
        Initialize state manager.
        
        Args:
            state_file: Path to the state file
        """
        self.state_file = state_file
        self.state: Dict = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load state from file or return empty state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # Convert completed_projects list back to set for internal use
                    if "completed_projects" in state and isinstance(state["completed_projects"], list):
                        state["completed_projects"] = set(state["completed_projects"])
                    logger.info(f"Loaded state from {self.state_file}")
                    return state
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load state: {e}. Starting fresh.")
                return self._empty_state()
        return self._empty_state()
    
    def _empty_state(self) -> Dict:
        """Return empty state structure."""
        return {
            "last_updated": None,
            "projects": {},
            "completed_projects": set(),
            "current_project": None,
            "current_issue_index": 0,
            "total_issues_scraped": 0
        }
    
    def save_state(self):
        """Save current state to file."""
        try:
            # Convert sets to lists for JSON serialization
            completed_projects = self.state.get("completed_projects", set())
            if isinstance(completed_projects, set):
                completed_projects = list(completed_projects)
            
            state_to_save = {
                **self.state,
                "completed_projects": completed_projects,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_to_save, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"State saved to {self.state_file}")
        except IOError as e:
            logger.error(f"Failed to save state: {e}")
    
    def is_project_completed(self, project: str) -> bool:
        """Check if a project has been completed."""
        completed = self.state.get("completed_projects", [])
        # Handle both set and list (from JSON)
        if isinstance(completed, set):
            return project in completed
        return project in completed
    
    def mark_project_completed(self, project: str):
        """Mark a project as completed."""
        if "completed_projects" not in self.state:
            self.state["completed_projects"] = set()
        # Ensure it's a set
        if isinstance(self.state["completed_projects"], list):
            self.state["completed_projects"] = set(self.state["completed_projects"])
        self.state["completed_projects"].add(project)
        self.save_state()
    
    def get_scraped_issues(self, project: str) -> Set[str]:
        """Get set of already scraped issue keys for a project."""
        if project not in self.state.get("projects", {}):
            return set()
        return set(self.state["projects"][project].get("scraped_issues", []))
    
    def mark_issue_scraped(self, project: str, issue_key: str):
        """Mark an issue as scraped."""
        if "projects" not in self.state:
            self.state["projects"] = {}
        if project not in self.state["projects"]:
            self.state["projects"][project] = {"scraped_issues": []}
        
        if issue_key not in self.state["projects"][project]["scraped_issues"]:
            self.state["projects"][project]["scraped_issues"].append(issue_key)
            self.state["total_issues_scraped"] = self.state.get("total_issues_scraped", 0) + 1
            self.save_state()
    
    def set_current_project(self, project: str):
        """Set the current project being scraped."""
        self.state["current_project"] = project
        self.save_state()
    
    def get_current_project(self) -> Optional[str]:
        """Get the current project being scraped."""
        return self.state.get("current_project")
    
    def reset(self):
        """Reset state (for testing or fresh start)."""
        self.state = self._empty_state()
        if self.state_file.exists():
            self.state_file.unlink()
        logger.info("State reset")

