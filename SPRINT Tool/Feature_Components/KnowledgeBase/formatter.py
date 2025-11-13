"""
Result formatter - formats retrieval results for SPRINT
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultFormatter:
    """Formats retrieval results for SPRINT comment generation"""
    
    def __init__(self):
        """Initialize result formatter"""
        logger.info("ResultFormatter initialized")
    
    def _get_syntax_highlight_language(self, language: str) -> str:
        """
        Map internal language name to markdown syntax highlighting
        
        Args:
            language: Internal language name (e.g., "python", "java")
            
        Returns:
            Markdown syntax highlighting language
        """
        mapping = {
            'python': 'python',
            'java': 'java'
        }
        return mapping.get(language, '')
    
    def aggregate_by_file(self, retrieval_results: List) -> List[Dict[str, Any]]:
        """
        Aggregate function results by file
        
        Args:
            retrieval_results: List of RetrievalResult objects
            
        Returns:
            List of file dictionaries with aggregated functions
        """
        # Group by file
        file_map = defaultdict(list)
        
        for result in retrieval_results:
            # Get language from result metadata
            language = getattr(result, 'language', 'python')
            
            file_map[result.file_path].append({
                'name': result.function_name,
                'signature': result.signature,
                'line_range': [result.start_line, result.end_line],
                'score': result.similarity_score,
                'class_name': result.class_name,
                'docstring': result.docstring,
                'language': language
            })
        
        # Convert to list and sort by highest function score
        file_list = []
        for file_path, functions in file_map.items():
            # Sort functions by score
            functions.sort(key=lambda x: x['score'], reverse=True)
            
            # Get language from first function (all functions in same file have same language)
            language = functions[0].get('language', 'python') if functions else 'python'
            
            file_list.append({
                'file_path': file_path,
                'score': functions[0]['score'],  # Use highest function score
                'functions': functions,
                'language': language
            })
        
        # Sort files by score
        file_list.sort(key=lambda x: x['score'], reverse=True)
        
        return file_list

    def extract_snippet(self, file_path: str, start_line: int, end_line: int, 
                       repo_path: str = "") -> str:
        """
        Extract code snippet from file
        
        Args:
            file_path: Relative file path
            start_line: Starting line number (1-based)
            end_line: Ending line number (1-based)
            repo_path: Repository root path
            
        Returns:
            Code snippet as string
        """
        try:
            # Construct full path
            if repo_path:
                full_path = Path(repo_path) / file_path
            else:
                full_path = Path(file_path)
            
            if not full_path.exists():
                logger.warning(f"File not found: {full_path}")
                return ""
            
            # Read file
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Validate line ranges
            if start_line < 1 or end_line > len(lines):
                logger.warning(f"Invalid line range: {start_line}-{end_line} for file with {len(lines)} lines")
                start_line = max(1, start_line)
                end_line = min(len(lines), end_line)
            
            # Extract lines (convert to 0-based indexing)
            snippet_lines = lines[start_line-1:end_line]
            snippet = ''.join(snippet_lines)
            
            # Limit snippet length
            if len(snippet) > 500:
                snippet = snippet[:500] + "\n..."
            
            return snippet
            
        except Exception as e:
            logger.error(f"Failed to extract snippet from {file_path}: {e}")
            return ""

    def format_results(self, retrieval_results: List, repo_info: Dict[str, Any], 
                      repo_path: str = "", top_n: int = 5) -> Dict[str, Any]:
        """
        Format retrieval results as JSON for SPRINT
        
        Args:
            retrieval_results: List of RetrievalResult objects
            repo_info: Dictionary with repo_name, commit_sha
            repo_path: Repository root path for snippet extraction
            top_n: Number of top functions to include snippets for
            
        Returns:
            Formatted dictionary
        """
        # Aggregate by file
        file_results = self.aggregate_by_file(retrieval_results)
        
        # Add snippets to top N functions
        snippet_count = 0
        for file_result in file_results:
            for func in file_result['functions']:
                if snippet_count < top_n:
                    snippet = self.extract_snippet(
                        file_result['file_path'],
                        func['line_range'][0],
                        func['line_range'][1],
                        repo_path
                    )
                    func['snippet'] = snippet
                    snippet_count += 1
                else:
                    func['snippet'] = None
        
        # Build output
        output = {
            'repository': repo_info.get('repo_name', ''),
            'commit_sha': repo_info.get('commit_sha', ''),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_results': len(retrieval_results),
            'top_files': file_results
        }
        
        logger.info(f"Formatted {len(file_results)} files with {len(retrieval_results)} functions")
        return output
