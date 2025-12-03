"""
Dense retriever - performs similarity search using FAISS
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from retrieval"""
    function_id: str
    function_name: str
    file_path: str
    class_name: Optional[str]
    start_line: int
    end_line: int
    signature: str
    docstring: Optional[str]
    similarity_score: float


class DenseRetriever:
    """Dense retrieval using FAISS similarity search"""
    
    def __init__(self, index_dir: str = "Data_Storage/KnowledgeBase"):
        """
        Initialize dense retriever
        
        Args:
            index_dir: Directory containing indices
        """
        self.index_dir = Path(index_dir)
        self.vector_store = VectorStore()
        self.loaded_repo = None
        
        logger.info("DenseRetriever initialized")
    
    def load_index(self, repo_name: str) -> bool:
        """
        Load FAISS index and metadata for a repository
        
        Args:
            repo_name: Repository name
            
        Returns:
            True if successful
        """
        # Try new format first (subdirectory)
        repo_dir = self.index_dir / repo_name.replace('/', '_')
        index_path = repo_dir / "index.faiss"
        metadata_path = repo_dir / "metadata.json"
        
        # Fallback to old format
        if not index_path.exists():
            index_path = self.index_dir / f"{repo_name.replace('/', '_')}.index"
            metadata_path = self.index_dir / f"{repo_name.replace('/', '_')}_metadata.json"
        
        if not index_path.exists():
            logger.error(f"Index not found for repository: {repo_name}")
            return False
        
        if not metadata_path.exists():
            logger.error(f"Metadata not found for repository: {repo_name}")
            return False
        
        # Load function index and metadata
        if not self.vector_store.load_index(str(index_path)):
            return False
        
        if not self.vector_store.load_metadata(str(metadata_path)):
            return False
            
        self.loaded_repo = repo_name
        logger.info(f"Loaded index for repository: {repo_name}")
        return True

    def retrieve(self, issue_embedding: np.ndarray, k: int = 10) -> List[RetrievalResult]:
        """
        Retrieve top-K most similar functions
        
        Args:
            issue_embedding: Issue embedding vector
            k: Number of results to return
            
        Returns:
            List of RetrievalResult objects sorted by score
        """
        if self.loaded_repo is None:
            logger.error("No index loaded. Call load_index() first")
            return []
        
        # Perform similarity search
        indices, scores, metadata_list = self.vector_store.search(issue_embedding, k)
        
        if not indices:
            logger.warning("No results found")
            return []
        
        # Convert to RetrievalResult objects
        results = []
        for idx, score, metadata in zip(indices, scores, metadata_list):
            try:
                result = RetrievalResult(
                    function_id=metadata.get('id', ''),
                    function_name=metadata.get('name', ''),
                    file_path=metadata.get('file_path', ''),
                    class_name=metadata.get('class_name'),
                    start_line=metadata.get('start_line', 0),
                    end_line=metadata.get('end_line', 0),
                    signature=metadata.get('signature', ''),
                    docstring=metadata.get('docstring'),
                    similarity_score=score
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to create result from metadata: {e}")
        
        logger.info(f"Retrieved {len(results)} results")
        return results

    def retrieve_files(self, issue_embedding: np.ndarray, k: int = 20) -> List[str]:
        """
        Retrieve top-K most relevant files by aggregating function scores.
        
        Args:
            issue_embedding: Issue embedding vector
            k: Number of files to return
            
        Returns:
            List of file paths
        """
        if self.loaded_repo is None:
            logger.error("No index loaded. Call load_index() first")
            return []
            
        # Retrieve a large number of functions to get good file coverage
        indices, scores, metadata_list = self.vector_store.search(issue_embedding, k=200)
        
        if not indices:
            return []
            
        file_scores = {}
        for idx, score, metadata in zip(indices, scores, metadata_list):
            file_path = metadata.get('file_path')
            if file_path:
                if file_path not in file_scores:
                    file_scores[file_path] = 0.0
                # Aggregate scores (max or sum? Max is better for "containing a buggy function")
                file_scores[file_path] = max(file_scores[file_path], score)
                
        # Sort by score
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return top k paths
        return [f[0] for f in sorted_files[:k]]
