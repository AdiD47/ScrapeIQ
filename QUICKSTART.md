# Quick Start Guide

## Installation (5 minutes)

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation:**
   ```bash
   python -c "import requests; print('✓ Setup successful!')"
   ```

## Running the Pipeline

### Basic Run
```bash
python main.py
```

This will:
- Scrape issues from SPARK, KAFKA, and HADOOP projects
- Save output to `data/jira_issues.jsonl`
- Save progress to `state/scraper_state.json`
- Log to `scraper.log` and console

### Resume After Interruption
If interrupted, simply run again:
```bash
python main.py
```
The system automatically resumes from where it left off.

## Verify Output

After scraping, verify the output:
```bash
python verify_output.py
```

This shows:
- Total issues scraped
- Project distribution
- Issue types and statuses
- Task generation statistics
- Sample issue

## Customization

Edit `config.py` to change:
- Projects to scrape
- Rate limiting
- Output location
- Safety limits

## Expected Output

- **Output file**: `data/jira_issues.jsonl` (JSONL format)
- **State file**: `state/scraper_state.json` (for resuming)
- **Log file**: `scraper.log` (detailed logs)

## Troubleshooting

**Connection issues?**
- Check internet connection
- Verify Apache Jira is accessible: https://issues.apache.org/jira

**Rate limiting?**
- Reduce `REQUESTS_PER_SECOND` in `config.py`
- Wait a few minutes and resume

**Want to start fresh?**
- Delete `state/scraper_state.json`
- Optionally delete `data/jira_issues.jsonl`

## Next Steps

See `README.md` for:
- Detailed architecture
- Edge cases handled
- Optimization decisions
- Future improvements

