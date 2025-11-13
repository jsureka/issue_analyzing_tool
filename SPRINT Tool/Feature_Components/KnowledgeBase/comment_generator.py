"""
Comment Generator - Generates structured GitHub comments for bug localization results
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CommentGenerator:
    """Generates markdown-formatted GitHub comments for bug localization results"""
    
    def __init__(self, repo_owner: str = "", repo_name: str = ""):
        """
        Initialize comment generator
        
        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        logger.info(f"CommentGenerator initialized for {repo_owner}/{repo_name}")
    
    def _get_confidence_badge(self, confidence: str, score: float) -> str:
        """
        Get confidence badge with emoji indicator and calibrated probability
        
        Args:
            confidence: Confidence level ("high", "medium", "low")
            score: Calibrated probability score (0-1)
            
        Returns:
            Formatted confidence badge string with emoji and percentage
        """
        confidence_lower = confidence.lower()
        
        # Map confidence to emoji and label
        if confidence_lower == "high":
            emoji = "🟢"
            label = "High"
            description = "Very likely to contain the bug"
        elif confidence_lower == "medium":
            emoji = "🟡"
            label = "Medium"
            description = "Possibly related to the bug"
        else:
            emoji = "🔴"
            label = "Low"
            description = "May require further investigation"
        
        # Convert score to percentage
        percentage = int(score * 100)
        
        # Format badge with emoji, percentage, and description
        badge = f"**Confidence:** {label} ({percentage}% probability) {emoji}\n\n"
        badge += f"*{description}*"
        
        return badge
    
    def format_confidence_badge(self, confidence: str, score: float) -> str:
        """
        Public method to format confidence badge
        
        Args:
            confidence: Confidence level ("high", "medium", "low")
            score: Calibrated probability score (0-1)
            
        Returns:
            Formatted confidence badge string
        """
        return self._get_confidence_badge(confidence, score)
    
    def _generate_github_permalink(self, file_path: str, start_line: int, 
                                   end_line: int, commit_sha: str) -> str:
        """
        Generate GitHub permalink URL with line ranges
        
        Args:
            file_path: Relative file path
            start_line: Starting line number
            end_line: Ending line number
            commit_sha: Git commit SHA
            
        Returns:
            GitHub permalink URL
        """
        if not self.repo_owner or not self.repo_name:
            return ""
        
        base_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/blob/{commit_sha}/{file_path}"
        
        if start_line == end_line:
            return f"{base_url}#L{start_line}"
        else:
            return f"{base_url}#L{start_line}-L{end_line}"
    
    def _format_code_snippet(self, code: str, language: str = "python", 
                            highlight_lines: Optional[List[int]] = None,
                            start_line: int = 1) -> str:
        """
        Format code snippet with markdown code fencing and line numbers
        
        Args:
            code: Code snippet text
            language: Programming language for syntax highlighting
            highlight_lines: Optional list of line numbers to highlight (relative to snippet)
            start_line: Starting line number for annotation
            
        Returns:
            Markdown-formatted code block with line numbers
        """
        if not code or not code.strip():
            return ""
        
        # Split code into lines
        lines = code.split('\n')
        
        # Add line number annotations if requested
        if highlight_lines:
            annotated_lines = []
            for i, line in enumerate(lines):
                line_num = start_line + i
                # Add highlight marker for specified lines
                if line_num in highlight_lines:
                    annotated_lines.append(f"{line}  # ⚠️ Line {line_num}")
                else:
                    annotated_lines.append(line)
            code = '\n'.join(annotated_lines)
        
        # Add code fencing with language for syntax highlighting
        formatted = f"```{language}\n{code}\n```"
        
        return formatted
    
    def _add_context_lines(self, snippet: str, context_before: int = 2, 
                          context_after: int = 2) -> str:
        """
        Add context lines before and after code snippet
        
        Args:
            snippet: Original code snippet
            context_before: Number of context lines before
            context_after: Number of context lines after
            
        Returns:
            Snippet with context indicators
        """
        if not snippet:
            return ""
        
        lines = snippet.split('\n')
        
        # Add context indicators
        if context_before > 0:
            lines.insert(0, "# ... (context above)")
        
        if context_after > 0:
            lines.append("# ... (context below)")
        
        return '\n'.join(lines)

    
    def _format_line_level_section(self, line_result: Dict[str, Any], rank: int,
                                   commit_sha: str) -> str:
        """
        Format a line-level result section
        
        Args:
            line_result: Line-level result dictionary
            rank: Result rank (1-based)
            commit_sha: Git commit SHA
            
        Returns:
            Markdown-formatted line-level section
        """
        function_name = line_result.get('function_name', 'unknown')
        file_path = line_result.get('file_path', '')
        line_start = line_result.get('line_start', 0)
        line_end = line_result.get('line_end', 0)
        score = line_result.get('score', 0.0)
        snippet = line_result.get('snippet', '')
        
        # Build section
        section = f"\n#### {rank}. `{function_name}` in `{file_path}`\n\n"
        section += f"**⚠️ Lines {line_start}-{line_end}** (Score: {score:.2f})\n\n"
        
        # Add permalink
        permalink = self._generate_github_permalink(file_path, line_start, line_end, commit_sha)
        if permalink:
            section += f"[View on GitHub]({permalink})\n\n"
        
        # Add code snippet with line highlights
        if snippet:
            section += self._format_code_snippet(snippet, "python")
            section += "\n"
        
        return section
    
    def _format_function_section(self, func_data: Dict[str, Any], rank: int, 
                                 file_path: str, commit_sha: str) -> str:
        """
        Format a single function section in the comment
        
        Args:
            func_data: Function data dictionary with name, signature, line_range, score, snippet
            rank: Function rank (1-based)
            file_path: File path containing the function
            commit_sha: Git commit SHA
            
        Returns:
            Markdown-formatted function section
        """
        func_name = func_data.get('name', 'unknown')
        signature = func_data.get('signature', '')
        line_range = func_data.get('line_range', [0, 0])
        score = func_data.get('score', 0.0)
        snippet = func_data.get('snippet', '')
        
        # Build section
        section = f"\n#### {rank}. `{func_name}` in `{file_path}` (Score: {score:.2f})\n\n"
        
        # Add line range and permalink
        permalink = self._generate_github_permalink(file_path, line_range[0], line_range[1], commit_sha)
        if permalink:
            section += f"**Lines {line_range[0]}-{line_range[1]}** | [View on GitHub]({permalink})\n\n"
        else:
            section += f"**Lines {line_range[0]}-{line_range[1]}**\n\n"
        
        # Add code snippet if available
        if snippet:
            section += self._format_code_snippet(snippet, "python")
            section += "\n"
        
        # Add explanation
        section += f"**Why this function?** High semantic similarity to issue description (score: {score:.2f}).\n"
        
        return section
    
    def generate_comment(self, results: Dict[str, Any], confidence: str = "medium", 
                        confidence_score: float = 0.5) -> str:
        """
        Generate complete GitHub comment from retrieval results
        
        Args:
            results: Formatted results dictionary from ResultFormatter
            confidence: Overall confidence level ("high", "medium", "low")
            confidence_score: Calibrated probability score (0-1)
            
        Returns:
            Markdown-formatted GitHub comment
        """
        try:
            # Extract data
            repo_name = results.get('repository', 'unknown')
            commit_sha = results.get('commit_sha', 'HEAD')
            timestamp = results.get('timestamp', datetime.utcnow().isoformat() + 'Z')
            total_results = results.get('total_results', 0)
            top_files = results.get('top_files', [])
            line_level_results = results.get('line_level_results', [])
            
            # Start building comment
            comment = "## 🔍 Bug Localization Results\n\n"
            
            # Add confidence badge
            comment += self._get_confidence_badge(confidence, confidence_score) + "\n\n"
            
            # Add intro
            comment += "I've analyzed this issue and identified the most likely locations for the bug:\n\n"
            
            # Add line-level results if available (Phase 3)
            if line_level_results:
                comment += "### 🎯 Precise Line-Level Locations\n\n"
                comment += "*Fine-grained analysis pinpointing specific line ranges:*\n\n"
                
                for i, line_result in enumerate(line_level_results[:3], 1):  # Top 3 line-level
                    comment += self._format_line_level_section(line_result, i, commit_sha)
                
                comment += "\n---\n\n"
            
            # Add top candidate functions (limit to top 5)
            comment += "### Top Candidate Functions\n"
            
            rank = 1
            for file_data in top_files[:5]:  # Limit to top 5 files
                file_path = file_data.get('file_path', '')
                functions = file_data.get('functions', [])
                
                # Add top function from each file (or multiple if same file)
                for func in functions[:2]:  # Max 2 functions per file
                    if rank > 5:  # Overall limit of 5 functions
                        break
                    comment += self._format_function_section(func, rank, file_path, commit_sha)
                    rank += 1
                
                if rank > 5:
                    break
            
            # Add summary section
            comment += "\n---\n\n### Summary\n\n"
            comment += f"- **Total functions analyzed:** {total_results:,}\n"
            comment += f"- **Commit:** `{commit_sha[:7]}...`\n"
            comment += f"- **Indexed:** {timestamp}\n\n"
            
            # Add confidence label info
            confidence_label = f"bug-localization:{confidence.lower()}-confidence"
            comment += f"**Labels applied:** `{confidence_label}`\n\n"
            
            # Add footer
            comment += "---\n\n"
            comment += "*This analysis was generated by SPRINT's Knowledge Base System.*\n"
            
            logger.info(f"Generated comment with {rank-1} functions, confidence: {confidence}")
            return comment
            
        except Exception as e:
            logger.error(f"Failed to generate comment: {e}")
            return self._generate_error_comment(str(e))
    
    def _generate_error_comment(self, error_msg: str) -> str:
        """
        Generate error comment when bug localization fails
        
        Args:
            error_msg: Error message
            
        Returns:
            Markdown-formatted error comment
        """
        comment = "## 🔍 Bug Localization Results\n\n"
        comment += "⚠️ **Error:** Unable to complete bug localization.\n\n"
        comment += f"```\n{error_msg}\n```\n\n"
        comment += "*Please check the logs for more details.*\n"
        return comment
