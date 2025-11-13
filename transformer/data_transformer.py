"""
Transform raw Jira data into structured JSONL format for LLM training.
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms Jira issues into LLM training format."""
    
    def __init__(self):
        """Initialize transformer."""
        pass
    
    def transform_issue(self, issue: Dict) -> Optional[Dict]:
        """
        Transform a single issue into training format.
        
        Args:
            issue: Raw issue dictionary from scraper
            
        Returns:
            Transformed issue dictionary or None if transformation fails
        """
        try:
            fields = issue.get("fields", {})
            issue_key = issue.get("key", "")
            
            # Extract basic metadata
            metadata = {
                "issue_key": issue_key,
                "project": fields.get("project", {}).get("key", ""),
                "project_name": fields.get("project", {}).get("name", ""),
                "issue_type": fields.get("issuetype", ""),
                "status": fields.get("status", ""),
                "priority": fields.get("priority", ""),
                "reporter": fields.get("reporter", ""),
                "assignee": fields.get("assignee", ""),
                "created": fields.get("created", ""),
                "updated": fields.get("updated", ""),
                "resolution_date": fields.get("resolutiondate", ""),
                "labels": fields.get("labels", []),
                "components": fields.get("components", []),
                "fix_versions": fields.get("fixVersions", [])
            }
            
            # Extract text content
            summary = self._clean_text(fields.get("summary", ""))
            description = self._extract_text_from_jira_markup(fields.get("description", ""))
            
            # Extract comments
            comments = fields.get("comments", [])
            comment_texts = []
            for comment in comments:
                author = comment.get("author", "")
                body = self._extract_text_from_jira_markup(comment.get("body", ""))
                created = comment.get("created", "")
                if body:
                    comment_texts.append({
                        "author": author,
                        "text": body,
                        "created": created
                    })
            
            # Combine all text content
            full_text = self._combine_text(summary, description, comment_texts)
            
            # Generate derived tasks
            tasks = self._generate_tasks(metadata, summary, description, comment_texts)
            
            # Create final structure
            transformed = {
                "metadata": metadata,
                "content": {
                    "summary": summary,
                    "description": description,
                    "comments": comment_texts,
                    "full_text": full_text
                },
                "tasks": tasks,
                "source": "apache_jira",
                "transformed_at": datetime.now().isoformat()
            }
            
            return transformed
            
        except Exception as e:
            logger.error(f"Failed to transform issue {issue.get('key', 'unknown')}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        return text.strip()
    
    def _extract_text_from_jira_markup(self, markup: str) -> str:
        """
        Extract plain text from Jira markup (basic implementation).
        
        Note: Jira uses a markup language. This is a simplified extractor.
        For production, consider using a proper Jira markup parser.
        """
        if not markup:
            return ""
        
        # Remove Jira markup tags (simplified)
        # Remove code blocks
        text = re.sub(r'\{code[^}]*\}(.*?)\{code\}', r'\1', markup, flags=re.DOTALL | re.IGNORECASE)
        # Remove noformat blocks
        text = re.sub(r'\{noformat\}(.*?)\{noformat\}', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove links [text|url] -> text
        text = re.sub(r'\[([^\]]+)\|[^\]]+\]', r'\1', text)
        # Remove simple links [url] -> url
        text = re.sub(r'\[([^\]]+)\]', r'\1', text)
        # Remove bold/italic markers
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        # Remove headers
        text = re.sub(r'^h[1-6]\.\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)
        # Remove lists
        text = re.sub(r'^[*#-]\s+', '', text, flags=re.MULTILINE)
        # Remove quotes
        text = re.sub(r'\{quote\}(.*?)\{quote\}', r'\1', text, flags=re.DOTALL | re.IGNORECASE)
        
        return self._clean_text(text)
    
    def _combine_text(self, summary: str, description: str, comments: List[Dict]) -> str:
        """Combine all text content into a single string."""
        parts = []
        
        if summary:
            parts.append(f"Summary: {summary}")
        
        if description:
            parts.append(f"\nDescription:\n{description}")
        
        if comments:
            parts.append("\nComments:")
            for comment in comments:
                author = comment.get("author", "Unknown")
                text = comment.get("text", "")
                if text:
                    parts.append(f"\n{author}: {text}")
        
        return "\n".join(parts)
    
    def _generate_tasks(self, metadata: Dict, summary: str, description: str, comments: List[Dict]) -> Dict:
        """
        Generate derived tasks for LLM training.
        
        Tasks include:
        - Summarization: Generate a summary of the issue
        - Classification: Classify the issue type, priority, etc.
        - QnA: Generate questions and answers from the issue
        """
        tasks = {}
        
        # Summarization task
        if summary or description:
            full_content = f"{summary}\n\n{description}".strip()
            if full_content:
                tasks["summarization"] = {
                    "input": full_content,
                    "target": summary if summary else self._generate_summary(full_content),
                    "task_type": "summarization"
                }
        
        # Classification tasks
        tasks["classification"] = {
            "input": f"{summary}\n\n{description}".strip(),
            "target": {
                "issue_type": metadata.get("issue_type", ""),
                "priority": metadata.get("priority", ""),
                "status": metadata.get("status", "")
            },
            "task_type": "classification"
        }
        
        # QnA generation
        qna_pairs = self._generate_qna(summary, description, comments)
        if qna_pairs:
            tasks["qa"] = {
                "pairs": qna_pairs,
                "task_type": "question_answering"
            }
        
        return tasks
    
    def _generate_summary(self, text: str) -> str:
        """
        Generate a simple summary (first sentence or first 100 chars).
        
        In a production system, this could use an LLM or more sophisticated
        summarization algorithm.
        """
        if not text:
            return ""
        
        # Simple heuristic: first sentence or first 100 characters
        sentences = re.split(r'[.!?]\s+', text)
        if sentences:
            return sentences[0][:200]
        return text[:200]
    
    def _generate_qna(self, summary: str, description: str, comments: List[Dict]) -> List[Dict]:
        """
        Generate question-answer pairs from issue content.
        
        This is a simplified implementation. In production, you might use
        an LLM to generate more sophisticated QnA pairs.
        """
        qna_pairs = []
        
        # Generate basic QnA pairs
        if summary:
            qna_pairs.append({
                "question": f"What is the issue about in {summary[:50]}...?",
                "answer": summary
            })
        
        if description:
            # Extract key sentences as potential answers
            sentences = re.split(r'[.!?]\s+', description)
            if sentences:
                first_sentence = sentences[0]
                if len(first_sentence) > 20:
                    qna_pairs.append({
                        "question": "What is the problem description?",
                        "answer": first_sentence
                    })
        
        # Generate QnA from comments
        for comment in comments[:3]:  # Limit to first 3 comments
            text = comment.get("text", "")
            if text and len(text) > 20:
                sentences = re.split(r'[.!?]\s+', text)
                if sentences:
                    qna_pairs.append({
                        "question": f"What did {comment.get('author', 'the user')} say?",
                        "answer": sentences[0]
                    })
        
        return qna_pairs
    
    def save_to_jsonl(self, transformed_issues: List[Dict], output_file: str):
        """
        Save transformed issues to JSONL file.
        
        Args:
            transformed_issues: List of transformed issue dictionaries
            output_file: Path to output JSONL file
        """
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                for issue in transformed_issues:
                    if issue:  # Skip None values
                        json_line = json.dumps(issue, ensure_ascii=False)
                        f.write(json_line + '\n')
            
            logger.info(f"Saved {len(transformed_issues)} issues to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save to {output_file}: {e}")
            raise

