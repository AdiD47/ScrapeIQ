# Apache Jira Data Scraping and Transformation Pipeline

A robust, fault-tolerant system for scraping public issue data from Apache's Jira instance and transforming it into a structured JSONL format suitable for training Large Language Models (LLMs).

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Setup](#setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Edge Cases Handled](#edge-cases-handled)
- [Optimization Decisions](#optimization-decisions)
- [Output Format](#output-format)
- [Future Improvements](#future-improvements)

## Overview

This pipeline extracts issue data from Apache Jira projects (SPARK, KAFKA, HADOOP) and converts it into a clean, structured dataset. The system is designed to handle real-world challenges including network failures, rate limiting, data inconsistencies, and interruptions.

## Features

### 1. **Robust Data Scraping**
- Fetches issues, comments, and comprehensive metadata from Apache Jira REST API
- Handles pagination automatically
- Respects rate limits with intelligent throttling
- Resume capability from last successful state

### 2. **Fault Tolerance**
- Automatic retry with exponential backoff
- Handles HTTP 429 (rate limiting) and 5xx errors gracefully
- Recovers from network failures and timeouts
- State persistence for resume after interruption

### 3. **Data Transformation**
- Converts raw Jira data to structured JSONL format
- Extracts and cleans text from Jira markup
- Generates derived tasks (summarization, classification, QnA)
- Handles missing or malformed data gracefully

### 4. **Optimization**
- Batch writing for efficiency
- Rate limiting to avoid API throttling
- Progress tracking with visual indicators
- Memory-efficient streaming processing

## Architecture

### System Components

```
┌─────────────────┐
│   main.py       │  ← Entry point and orchestration
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────────┐
│Scraper│ │Transformer│
└───┬───┘ └───┬───────┘
    │         │
┌───▼─────────▼───┐
│  JiraClient     │  ← API interaction with rate limiting
└─────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────────┐
│ State │ │ RateLimiter │
│Manager│ │   Retry     │
└───────┘ └─────────────┘
```

### Key Modules

1. **`scraper/jira_client.py`**: 
   - Handles all API interactions
   - Implements rate limiting and retry logic
   - Manages HTTP errors and timeouts

2. **`scraper/data_scraper.py`**:
   - Orchestrates issue fetching
   - Handles pagination
   - Enriches issues with comments

3. **`transformer/data_transformer.py`**:
   - Transforms raw data to training format
   - Extracts text from Jira markup
   - Generates derived tasks

4. **`utils/state_manager.py`**:
   - Tracks scraping progress
   - Enables resume capability
   - Persists state to disk

5. **`utils/rate_limiter.py`**:
   - Token bucket algorithm for rate limiting
   - Thread-safe implementation

6. **`utils/retry.py`**:
   - Exponential backoff retry logic
   - Handles retryable vs non-retryable errors

## Setup

### Prerequisites

- Python 3.8 or higher
- Internet connection to access Apache Jira API

### Installation

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd /path/to/project
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```bash
   python -c "import requests; print('Setup successful!')"
   ```

## Usage

### Basic Usage

Run the pipeline with default settings:

```bash
python main.py
```

The pipeline will:
1. Connect to Apache Jira API
2. Scrape issues from configured projects (SPARK, KAFKA, HADOOP)
3. Transform data to JSONL format
4. Save output to `data/jira_issues.jsonl`
5. Save state to `state/scraper_state.json`

### Resuming Interrupted Scraping

If the pipeline is interrupted (Ctrl+C, crash, etc.), simply run it again:

```bash
python main.py
```

The system will automatically resume from the last successful state, skipping already-scraped issues.

### Configuration

Edit `config.py` to customize:

- **Projects**: Change `PROJECTS` list to scrape different Apache projects
- **Rate Limiting**: Adjust `REQUESTS_PER_SECOND` (default: 2)
- **Pagination**: Modify `ISSUES_PER_PAGE` (default: 100)
- **Output**: Change `OUTPUT_FILE` path
- **Safety Limits**: Adjust `MAX_ISSUES_PER_PROJECT` (default: 10000)

### Logging

Logs are written to:
- Console (stdout)
- File: `scraper.log`

Log levels can be adjusted in `main.py`:
```python
logging.basicConfig(level=logging.INFO)  # Change to DEBUG for verbose output
```

## Configuration

### Key Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `PROJECTS` | `["SPARK", "KAFKA", "HADOOP"]` | Apache projects to scrape |
| `REQUESTS_PER_SECOND` | `2` | API rate limit (requests/second) |
| `MAX_RETRIES` | `5` | Maximum retry attempts |
| `TIMEOUT` | `30` | Request timeout (seconds) |
| `ISSUES_PER_PAGE` | `100` | Issues per API request |
| `MAX_ISSUES_PER_PROJECT` | `10000` | Safety limit per project |

## Edge Cases Handled

### 1. **Network Failures**
- **Connection Errors**: Retried with exponential backoff
- **Timeouts**: Configurable timeout with retry
- **DNS Failures**: Caught and logged, retried

### 2. **HTTP Errors**
- **429 (Rate Limiting)**: 
  - Detects `Retry-After` header
  - Waits appropriate duration
  - Automatically retries
- **5xx (Server Errors)**: 
  - Retried with exponential backoff
  - Maximum retry limit enforced
- **404 (Not Found)**: 
  - Logged as warning
  - Skipped gracefully
- **Other 4xx Errors**: 
  - Logged and not retried (client errors)

### 3. **Data Inconsistencies**
- **Missing Fields**: 
  - Default values provided (empty strings, empty lists)
  - No crashes on missing data
- **Null/None Values**: 
  - Converted to appropriate defaults
  - Handled in all data extraction paths
- **Malformed Jira Markup**: 
  - Basic markup extraction implemented
  - Falls back to raw text if parsing fails
- **Empty Issues**: 
  - Skipped or handled with minimal data
  - No crashes on empty responses

### 4. **Interruptions**
- **Keyboard Interrupt (Ctrl+C)**: 
  - State saved immediately
  - Current batch written to file
  - Can resume seamlessly
- **Process Crashes**: 
  - State persisted after each issue
  - Last successful state recovered on restart

### 5. **Rate Limiting**
- **Token Bucket Algorithm**: 
  - Prevents exceeding rate limits
  - Thread-safe implementation
- **Dynamic Backoff**: 
  - Respects `Retry-After` headers
  - Exponential backoff for retries

### 6. **Pagination Edge Cases**
- **Empty Pages**: Detected and handled
- **Inconsistent Page Sizes**: Handled gracefully
- **Total Count Mismatches**: Progress tracking adapts

### 7. **File I/O Errors**
- **Permission Errors**: Logged with clear messages
- **Disk Full**: Caught and logged
- **Encoding Issues**: UTF-8 with error handling

## Optimization Decisions

### 1. **Rate Limiting Strategy**
- **Decision**: Token bucket algorithm with 2 requests/second
- **Rationale**: 
  - Prevents API throttling
  - Respects Apache Jira's rate limits
  - Conservative to avoid being blocked
- **Trade-off**: Slower scraping but more reliable

### 2. **Batch Writing**
- **Decision**: Write to JSONL in batches of 10 issues
- **Rationale**: 
  - Reduces I/O operations
  - Balances memory usage and performance
  - Ensures data persistence even on interruption
- **Trade-off**: Small delay in seeing results, but better performance

### 3. **State Persistence**
- **Decision**: Save state after each issue
- **Rationale**: 
  - Maximum fault tolerance
  - Minimal data loss on interruption
- **Trade-off**: More I/O, but critical for reliability

### 4. **Synchronous Processing**
- **Decision**: Sequential API requests (not async)
- **Rationale**: 
  - Simpler error handling
  - Easier to respect rate limits
  - More predictable behavior
- **Trade-off**: Could be faster with async, but complexity not worth it for this use case

### 5. **Jira Markup Parsing**
- **Decision**: Basic regex-based extraction
- **Rationale**: 
  - No external dependencies
  - Handles most common cases
  - Fast and lightweight
- **Trade-off**: May miss some edge cases, but covers 90%+ of content

### 6. **Memory Efficiency**
- **Decision**: Stream processing (yield issues one at a time)
- **Rationale**: 
  - Can handle large datasets
  - Low memory footprint
  - Suitable for long-running processes
- **Trade-off**: Slightly more complex code, but essential for scalability

## Output Format

### JSONL Structure

Each line in the output file is a JSON object with the following structure:

```json
{
  "metadata": {
    "issue_key": "SPARK-12345",
    "project": "SPARK",
    "project_name": "Apache Spark",
    "issue_type": "Bug",
    "status": "Resolved",
    "priority": "Major",
    "reporter": "John Doe",
    "assignee": "Jane Smith",
    "created": "2023-01-15T10:30:00.000+0000",
    "updated": "2023-01-20T15:45:00.000+0000",
    "resolution_date": "2023-01-20T15:45:00.000+0000",
    "labels": ["bug", "critical"],
    "components": ["Core"],
    "fix_versions": ["3.4.0"]
  },
  "content": {
    "summary": "Issue summary text",
    "description": "Full issue description",
    "comments": [
      {
        "author": "Commenter Name",
        "text": "Comment text",
        "created": "2023-01-16T12:00:00.000+0000"
      }
    ],
    "full_text": "Combined summary, description, and comments"
  },
  "tasks": {
    "summarization": {
      "input": "Full content text",
      "target": "Summary text",
      "task_type": "summarization"
    },
    "classification": {
      "input": "Full content text",
      "target": {
        "issue_type": "Bug",
        "priority": "Major",
        "status": "Resolved"
      },
      "task_type": "classification"
    },
    "qa": {
      "pairs": [
        {
          "question": "What is the issue about?",
          "answer": "Issue summary"
        }
      ],
      "task_type": "question_answering"
    }
  },
  "source": "apache_jira",
  "transformed_at": "2024-01-15T10:30:00.000000"
}
```

### Task Types

1. **Summarization**: Input is full content, target is summary
2. **Classification**: Input is content, target is metadata (type, priority, status)
3. **Question Answering**: Generated QnA pairs from issue content

## Future Improvements

### 1. **Enhanced Markup Parsing**
- Use a proper Jira markup parser library
- Better handling of code blocks, tables, attachments
- Preserve formatting where useful

### 2. **Async Processing**
- Implement async/await for concurrent requests
- Better utilization of rate limits
- Faster overall scraping

### 3. **Advanced Task Generation**
- Use LLM APIs to generate better summaries
- Create more sophisticated QnA pairs
- Generate additional training tasks (e.g., code generation, bug fixing)

### 4. **Data Quality Metrics**
- Track data quality scores
- Identify and flag low-quality issues
- Generate data quality reports

### 5. **Incremental Updates**
- Track issue updates
- Only fetch changed issues
- Maintain version history

### 6. **Parallel Project Scraping**
- Scrape multiple projects concurrently
- Better resource utilization
- Faster completion

### 7. **Database Backend**
- Store data in database instead of JSONL
- Enable querying and filtering
- Better for large-scale operations

### 8. **Monitoring and Alerting**
- Real-time progress dashboard
- Alert on failures or rate limits
- Performance metrics tracking

### 9. **Configuration Management**
- YAML/JSON config files
- Environment-specific settings
- Command-line argument parsing

### 10. **Testing**
- Unit tests for all components
- Integration tests
- Mock API responses for testing

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check internet connection
   - Increase `TIMEOUT` in `config.py`
   - Verify Apache Jira is accessible

2. **Rate Limiting**
   - Reduce `REQUESTS_PER_SECOND` in `config.py`
   - Wait and resume later
   - Check if IP is temporarily blocked

3. **State File Corruption**
   - Delete `state/scraper_state.json` to start fresh
   - Or manually edit to fix issues

4. **Memory Issues**
   - Reduce `ISSUES_PER_PAGE` in `config.py`
   - Process projects one at a time

5. **Empty Output**
   - Check logs in `scraper.log`
   - Verify projects exist and have issues
   - Check API connectivity

## License

This project is for educational purposes. Please respect Apache Jira's terms of service and rate limits.

## Contributing

This is an assignment project. For improvements or questions, please refer to the assignment guidelines.

## Acknowledgments

- Apache Software Foundation for providing public Jira access
- Jira REST API documentation
- Python community for excellent libraries

---

**Note**: This pipeline is designed to be respectful of Apache Jira's resources. It implements conservative rate limiting and handles errors gracefully. Always respect the terms of service of any API you interact with.

