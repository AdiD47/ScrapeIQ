"""
Utility script to verify and analyze the output JSONL file.
"""
import json
import sys
from pathlib import Path
from collections import Counter
import config


def analyze_output(file_path: Path):
    """Analyze the output JSONL file and print statistics."""
    if not file_path.exists():
        print(f"Error: Output file not found at {file_path}")
        return
    
    issues = []
    total_lines = 0
    
    print(f"Reading {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            total_lines += 1
            try:
                issue = json.loads(line.strip())
                issues.append(issue)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
    
    if not issues:
        print("No valid issues found in output file.")
        return
    
    print("\n" + "=" * 60)
    print("OUTPUT ANALYSIS")
    print("=" * 60)
    print(f"\nTotal issues: {len(issues)}")
    print(f"Total lines processed: {total_lines}")
    
    # Project distribution
    projects = Counter(issue['metadata']['project'] for issue in issues)
    print(f"\nProjects distribution:")
    for project, count in projects.most_common():
        print(f"  {project}: {count}")
    
    # Issue types
    issue_types = Counter(issue['metadata']['issue_type'] for issue in issues)
    print(f"\nIssue types:")
    for itype, count in issue_types.most_common(10):
        print(f"  {itype}: {count}")
    
    # Status distribution
    statuses = Counter(issue['metadata']['status'] for issue in issues)
    print(f"\nStatus distribution:")
    for status, count in statuses.most_common(10):
        print(f"  {status}: {count}")
    
    # Tasks statistics
    tasks_with_summarization = sum(1 for issue in issues if 'summarization' in issue.get('tasks', {}))
    tasks_with_classification = sum(1 for issue in issues if 'classification' in issue.get('tasks', {}))
    tasks_with_qa = sum(1 for issue in issues if 'qa' in issue.get('tasks', {}))
    
    print(f"\nTasks generated:")
    print(f"  Summarization: {tasks_with_summarization}")
    print(f"  Classification: {tasks_with_classification}")
    print(f"  QnA: {tasks_with_qa}")
    
    # Content statistics
    issues_with_description = sum(1 for issue in issues if issue['content']['description'])
    issues_with_comments = sum(1 for issue in issues if issue['content']['comments'])
    total_comments = sum(len(issue['content']['comments']) for issue in issues)
    
    print(f"\nContent statistics:")
    print(f"  Issues with description: {issues_with_description}")
    print(f"  Issues with comments: {issues_with_comments}")
    print(f"  Total comments: {total_comments}")
    
    # Sample issue
    print(f"\n" + "=" * 60)
    print("SAMPLE ISSUE (first issue):")
    print("=" * 60)
    if issues:
        sample = issues[0]
        print(json.dumps(sample, indent=2, ensure_ascii=False)[:1000] + "...")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    output_file = config.OUTPUT_FILE
    if len(sys.argv) > 1:
        output_file = Path(sys.argv[1])
    
    analyze_output(output_file)

