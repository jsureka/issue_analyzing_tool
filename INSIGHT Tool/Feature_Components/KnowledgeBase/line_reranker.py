"""
Line-Level Reranker - Provides fine-grained localization within functions
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from .vector_store import WindowVectorStore

logger = logging.getLogger(__name__)


@dataclass
class LineResult:
    """Result of line-level localization"""
    function_id: str
    function_name: str
    file_path: str
    line_start: int
    line_end: int
    snippet: str
    similarity_score: float
    confidence: str = "medium"
    confidence_score: float = 0.5


class LineReranker:
    """Reranks functions at line-level using window embeddings"""
    
    def __init__(self, window_size: int = 48):
        """
        Initialize line reranker
        
        Args:
            window_size: Size of line windows in tokens
        """
        self.window_size = window_size
        self.window_store = None
        logger.info(f"LineReranker initialized with window_size={window_size}")
    
    def load_window_index(self, repo_name: str, index_path: str, metadata_path: str) -> bool:
        """
        Load window index and metadata
        
        Args:
            repo_name: Repository name
            index_path: Path to window FAISS index
            metadata_path: Path to window metadata JSON
            
        Returns:
            True if successful
        """
        try:
            self.window_store = WindowVectorStore()
            
            # Load index
            if not self.window_store.load_index(index_path):
                logger.error(f"Failed to load window index: {index_path}")
                return False
            
            # Load metadata
            if not self.window_store.load_window_metadata(metadata_path):
                logger.error(f"Failed to load window metadata: {metadata_path}")
                return False
            
            logger.info(f"Loaded window index for {repo_name}: {self.window_store.index.ntotal} windows")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load window index: {e}")
            return False
    
    def rerank_functions(self, issue_embedding: np.ndarray, 
                        function_results: List[Dict[str, Any]]) -> List[LineResult]:
        """
        Rerank functions at line-level by finding best windows
        
        Args:
            issue_embedding: Issue embedding vector
            function_results: List of function-level retrieval results
            
        Returns:
            List of LineResult objects with line-level localization
        """
        if self.window_store is None:
            logger.warning("Window store not loaded")
            return []
        
        line_results = []
        
        for func_result in function_results:
            try:
                function_id = func_result.get('function_id', '')
                function_name = func_result.get('function_name', '')
                file_path = func_result.get('file_path', '')
                
                # Get all windows for this function
                function_windows = self.window_store.get_windows_for_function(function_id)
                
                if not function_windows:
                    logger.debug(f"No windows found for function {function_name}")
                    # Return function-level result as fallback
                    line_results.append(LineResult(
                        function_id=function_id,
                        function_name=function_name,
                        file_path=file_path,
                        line_start=func_result.get('start_line', 0),
                        line_end=func_result.get('end_line', 0),
                        snippet=func_result.get('snippet', ''),
                        similarity_score=func_result.get('similarity_score', 0.0)
                    ))
                    continue
                
                # Search windows for this function
                best_window = self._find_best_window(issue_embedding, function_windows)
                
                if best_window:
                    line_results.append(LineResult(
                        function_id=function_id,
                        function_name=function_name,
                        file_path=file_path,
                        line_start=best_window['line_start'],
                        line_end=best_window['line_end'],
                        snippet=best_window['text'],
                        similarity_score=best_window['score']
                    ))
                
            except Exception as e:
                logger.error(f"Failed to rerank function {func_result.get('function_name')}: {e}")
                continue
        
        # Sort by score
        line_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        logger.info(f"Reranked {len(line_results)} functions at line-level")
        return line_results
    
    def _find_best_window(self, issue_embedding: np.ndarray, 
                         function_windows: List[Dict]) -> Dict[str, Any]:
        """
        Find the best matching window within a function using local reranking
        
        Args:
            issue_embedding: Issue embedding vector
            function_windows: List of window metadata for the function
            
        Returns:
            Best window dictionary with score
        """
        if not function_windows:
            return None
        
        try:
            # Get window indices
            window_indices = [w['index'] for w in function_windows]
            
            # Compute similarity for each window
            # We need to get embeddings from the FAISS index
            best_window = None
            best_score = -1.0
            
            # Normalize issue embedding
            issue_norm = np.linalg.norm(issue_embedding)
            if issue_norm > 0:
                issue_embedding_normalized = issue_embedding / issue_norm
            else:
                issue_embedding_normalized = issue_embedding
            
            # For each window, compute similarity
            for window_meta in function_windows:
                window_idx = window_meta['index']
                
                if window_idx >= self.window_store.index.ntotal:
                    continue
                
                # Get window embedding from FAISS index
                # FAISS stores normalized vectors, so we can use them directly
                window_embedding = self.window_store.index.reconstruct(int(window_idx))
                
                # Compute inner product (cosine similarity for normalized vectors)
                similarity = np.dot(issue_embedding_normalized, window_embedding)
                
                if similarity > best_score:
                    best_score = similarity
                    best_window = window_meta.copy()
                    best_window['score'] = float(similarity)
            
            if best_window:
                logger.debug(f"Best window score: {best_score:.3f} at lines {best_window.get('line_start')}-{best_window.get('line_end')}")
            
            return best_window
            
        except Exception as e:
            logger.error(f"Error finding best window: {e}")
            # Fallback: use first window
            if function_windows:
                best_window = function_windows[0].copy()
                best_window['score'] = 0.5
                return best_window
            return None
    
    def extract_line_range(self, window_metadata: Dict[str, Any], 
                          file_path: str = "", repo_path: str = "",
                          context_lines: int = 2) -> Tuple[int, int, str]:
        """
        Extract line range with context from window metadata
        
        Args:
            window_metadata: Window metadata dictionary
            file_path: File path for reading actual content
            repo_path: Repository root path
            context_lines: Number of context lines before/after
            
        Returns:
            Tuple of (start_line, end_line, snippet_with_context)
        """
        line_start = window_metadata.get('line_start', 0)
        line_end = window_metadata.get('line_end', 0)
        snippet = window_metadata.get('text', '')
        
        # Try to read actual file content for better snippet
        if file_path and repo_path:
            try:
                from pathlib import Path
                full_path = Path(repo_path) / file_path
                
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    # Extract with context
                    start_idx = max(0, line_start - 1 - context_lines)
                    end_idx = min(len(lines), line_end + context_lines)
                    
                    context_lines_list = lines[start_idx:end_idx]
                    snippet_with_context = ''.join(context_lines_list)
                    
                    # Add line number annotations
                    annotated_lines = []
                    for i, line in enumerate(context_lines_list):
                        actual_line_num = start_idx + i + 1
                        # Mark the target range
                        if line_start <= actual_line_num <= line_end:
                            annotated_lines.append(f"{line.rstrip()}  # ⚠️ Line {actual_line_num}\n")
                        else:
                            annotated_lines.append(line)
                    
                    snippet_with_context = ''.join(annotated_lines)
                    return line_start, line_end, snippet_with_context
                    
            except Exception as e:
                logger.warning(f"Could not read file for line range: {e}")
        
        # Fallback: use window text with context indicators
        snippet_with_context = f"# ... (context above)\n{snippet}\n# ... (context below)"
        
        return line_start, line_end, snippet_with_context
