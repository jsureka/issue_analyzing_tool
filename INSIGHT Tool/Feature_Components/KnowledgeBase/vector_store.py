"""
FAISS vector store for code embeddings
Manages similarity search and metadata
"""

import logging
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

try:
    import faiss
except ImportError:
    raise ImportError("faiss-cpu is required. Install with: pip install faiss-cpu")

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for function embeddings"""
    
    def __init__(self, dimension: int = 768):
        """
        Initialize vector store
        
        Args:
            dimension: Embedding dimension (768 for UniXcoder/GraphCodeBERT)
        """
        self.dimension = dimension
        self.index = None
        self.metadata = []
        
        logger.info(f"VectorStore initialized with dimension: {dimension}")
    
    def create_index(self):
        """Create a new FAISS index using IndexFlatIP (inner product)"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        logger.info("Created new FAISS IndexFlatIP")
    
    def save_index(self, index_path: str) -> bool:
        """
        Save FAISS index to disk
        
        Args:
            index_path: Path to save the index file
            
        Returns:
            True if successful
        """
        if self.index is None:
            logger.error("No index to save")
            return False
        
        try:
            # Create directory if needed
            Path(index_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save index
            faiss.write_index(self.index, index_path)
            logger.info(f"Saved FAISS index to: {index_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def load_index(self, index_path: str) -> bool:
        """
        Load FAISS index from disk
        
        Args:
            index_path: Path to the index file
            
        Returns:
            True if successful
        """
        try:
            self.index = faiss.read_index(index_path)
            logger.info(f"Loaded FAISS index from: {index_path}")
            logger.info(f"Index contains {self.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def add_vectors(self, embeddings: np.ndarray, metadata_list: List[Dict[str, Any]]) -> bool:
        """
        Add vectors and their metadata to the index
        
        Args:
            embeddings: Numpy array of embeddings (n x dimension)
            metadata_list: List of metadata dicts for each embedding
            
        Returns:
            True if successful
        """
        if self.index is None:
            logger.error("Index not created. Call create_index() first")
            return False
        
        if len(embeddings) != len(metadata_list):
            logger.error("Number of embeddings must match number of metadata entries")
            return False
        
        try:
            # Ensure embeddings are float32
            if embeddings.dtype != np.float32:
                embeddings = embeddings.astype(np.float32)
            
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Add metadata with index positions
            start_idx = len(self.metadata)
            for i, meta in enumerate(metadata_list):
                meta['index'] = start_idx + i
                self.metadata.append(meta)
            
            logger.info(f"Added {len(embeddings)} vectors to index")
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False
    
    def save_metadata(self, metadata_path: str) -> bool:
        """
        Save metadata to JSON file
        
        Args:
            metadata_path: Path to save metadata file
            
        Returns:
            True if successful
        """
        try:
            # Create directory if needed
            Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info(f"Saved metadata to: {metadata_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            return False
    
    def load_metadata(self, metadata_path: str) -> bool:
        """
        Load metadata from JSON file
        
        Args:
            metadata_path: Path to metadata file
            
        Returns:
            True if successful
        """
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            logger.info(f"Loaded {len(self.metadata)} metadata entries from: {metadata_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return False

    def search(self, query_embedding: np.ndarray, k: int = 10) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        """
        Search for top-K most similar vectors
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            Tuple of (indices, scores, metadata_list)
        """
        if self.index is None:
            logger.error("Index not loaded")
            return [], [], []
        
        if self.index.ntotal == 0:
            logger.warning("Index is empty")
            return [], [], []
        
        try:
            # Ensure query is 2D array and float32
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            if query_embedding.dtype != np.float32:
                query_embedding = query_embedding.astype(np.float32)
            
            # Limit k to available vectors
            k = min(k, self.index.ntotal)
            
            # Search
            scores, indices = self.index.search(query_embedding, k)
            
            # Flatten results (since we have single query)
            scores = scores[0].tolist()
            indices = indices[0].tolist()
            
            # Normalize scores to [0, 1] range
            # Inner product scores can be negative, so we normalize
            if scores:
                min_score = min(scores)
                max_score = max(scores)
                # if max_score > min_score:
                #     scores = [(s - min_score) / (max_score - min_score) for s in scores]
                # else:
                #     scores = [1.0] * len(scores)
                pass
            
            # Get corresponding metadata
            result_metadata = []
            for idx in indices:
                if 0 <= idx < len(self.metadata):
                    result_metadata.append(self.metadata[idx])
                else:
                    logger.warning(f"Index {idx} out of metadata range")
                    result_metadata.append({})
            
            logger.info(f"Found {len(indices)} results")
            return indices, scores, result_metadata
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [], [], []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store
        
        Returns:
            Dictionary with stats
        """
        stats = {
            'dimension': self.dimension,
            'total_vectors': self.index.ntotal if self.index else 0,
            'metadata_count': len(self.metadata)
        }
        return stats




