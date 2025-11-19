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
        index_path = self.index_dir / repo_name.replace('/', '_') / "index.faiss"
        metadata_path = self.index_dir / repo_name.replace('/', '_') / "metadata.json"
        
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
        
        # Load index and metadata
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
