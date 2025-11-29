"""
Configuration settings for the Jira scraping pipeline.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Apache Jira base URL
JIRA_BASE_URL = "https://issues.apache.org/jira/rest/api/2"

# Projects to scrape (choose 3 Apache projects)
# Using popular projects: SPARK, KAFKA, HADOOP
PROJECTS = ["SPARK", "KAFKA", "HADOOP"]

# Rate limiting
REQUESTS_PER_SECOND = 2  # Conservative rate limit
MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds
TIMEOUT = 60  # seconds (increased for slow responses)
CONNECT_TIMEOUT = 10  # seconds for connection establishment
READ_TIMEOUT = 60  # seconds for reading response

# Pagination
ISSUES_PER_PAGE = 100
MAX_ISSUES_PER_PROJECT = 10000  # Safety limit

# Output directories
DATA_DIR = BASE_DIR / "data"
STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# State file
STATE_FILE = STATE_DIR / "scraper_state.json"

# Output file
OUTPUT_FILE = DATA_DIR / "jira_issues.jsonl"

# Output format: "jsonl" or "toon"
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "jsonl").lower()

# TON output file (used when OUTPUT_FORMAT == "toon")
TOON_OUTPUT_FILE = DATA_DIR / "jira_issues.toon"

# Fields to extract
ISSUE_FIELDS = [
    "summary",
    "description",
    "status",
    "priority",
    "assignee",
    "reporter",
    "created",
    "updated",
    "resolutiondate",
    "labels",
    "components",
    "fixVersions",
    "issuetype",
    "project",
    "comment",
]

