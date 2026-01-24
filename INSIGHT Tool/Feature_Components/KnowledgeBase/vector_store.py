"""
FAISS vector store for code embeddings
Manages similarity search and metadata
"""

import logging
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import math
from collections import Counter

try:
    import faiss
except ImportError:
    raise ImportError("faiss-cpu is required. Install with: pip install faiss-cpu")

logger = logging.getLogger(__name__)

# --- BM25 / Sparse Search Support ---

class SimpleBM25:
    """
    Zero-dependency BM25 implementation.
    Optimized for indexing metadata strings on the fly.
    """
    def __init__(self, corpus: List[str]):
        self.corpus_size = len(corpus)
        self.avgdl = 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.corpus = corpus
        self._initialize()

    def _initialize(self):
        total_len = 0
        for doc in self.corpus:
            tokens = self._tokenize(doc)
            self.doc_len.append(len(tokens))
            total_len += len(tokens)
            
            frequencies = Counter(tokens)
            self.doc_freqs.append(frequencies)
            
            for token in frequencies:
                self.idf[token] = self.idf.get(token, 0) + 1
        
        self.avgdl = total_len / self.corpus_size if self.corpus_size > 0 else 0
        
        # Calculate IDF
        for token, freq in self.idf.items():
            self.idf[token] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def _tokenize(self, text: str) -> List[str]:
        # Improved Regex Tokenizer for Code
        # Captures: identifiers, dot.separated, snake_case
        # Splits on non-word characters but keeps meaningful code punctuation if needed?
        # User suggested: r"[A-Za-z_][A-Za-z0-9_\.]*" to keep dot-separated paths/calls together or split?
        # "FooService.process" -> "FooService.process" might be good for exact match, 
        # but "FooService" and "process" separate is better for flexible match.
        # User suggestion: re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", text) -> keeps dots.
        # Let's use a slightly more granular approach: split on non-alphanum but keep underscores.
        # actually, let's follow the user's specific regex suggestion first as it seems well reasoned for this codebase.
        
        import re
        # Find all sequences of word chars (including dots for namespaces/files)
        # But this might merge 'obj.method' into one token.
        # If the query is 'method', it won't match 'obj.method' in BM25 unless we iterate.
        # Better: Standard tokenizer `\w+`.
        return [t.lower() for t in re.findall(r"\w+", text)]

    def get_scores(self, query: str) -> List[float]:
        tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size
        
        # Hyperparameters
        k1 = 1.5
        b = 0.75
        
        for token in tokens:
            if token not in self.idf:
                continue
            
            idf = self.idf[token]
            
            for index, freq_map in enumerate(self.doc_freqs):
                freq = freq_map.get(token, 0)
                if freq == 0: continue
                
                doc_len = self.doc_len[index]
                score = idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * (doc_len / self.avgdl)))
                scores[index] += score
                
        return scores

    def search(self, query: str, k: int = 10) -> Tuple[List[int], List[float]]:
        scores = self.get_scores(query)
        # Get top k indices
        # Argpartition or sort
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        top_scores = [scores[i] for i in top_indices]
        return top_indices, top_scores


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
        self.bm25 = None
        
        logger.info(f"VectorStore initialized with dimension: {dimension}")
    
    def _l2_normalize(self, x: np.ndarray) -> np.ndarray:
        """Normalize vectors to unit length for Cosine Similarity via Inner Product"""
        if x.ndim == 1:
            x = x.reshape(1, -1)
        # Avoid division by zero
        norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
        return (x / norms).astype(np.float32)

    def create_index(self):
        """Create a new FAISS index using IndexFlatIP (inner product)"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self.bm25 = None
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
            
            # Normalize before adding
            embeddings = self._l2_normalize(embeddings)

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

    def get_metadata_by_id(self, id_str: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata by string ID (e.g. from Graph)"""
        # Linear scan for now - fast enough for <10k functions
        # Optimized: could build distinct dict on load
        for meta in self.metadata:
            if meta.get('id') == id_str:
                return meta
        return None

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
            
            # Normalize query
            query_embedding = self._l2_normalize(query_embedding)
            
            # Limit k to available vectors
            k = min(k, self.index.ntotal)
            
            # Search
            scores, indices = self.index.search(query_embedding, k)
            
            # Flatten results (since we have single query)
            scores = scores[0].tolist()
            indices = indices[0].tolist()
            
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

    def build_bm25(self):
        """Build BM25 index from current metadata"""
        logger.info("Building BM25 index from metadata...")
        corpus = []
        for meta in self.metadata:
            # Construct meaningful text from metadata
            # Name + Signature + Docstring + FilePath
            text = f"{meta.get('name', '')} {meta.get('file_path', '')} {meta.get('signature', '')} {meta.get('docstring', '')}"
            corpus.append(text)
        
        self.bm25 = SimpleBM25(corpus)
        logger.info("BM25 index built.")

    def search_hybrid(self, query_dense: np.ndarray, query_text: str, k: int = 10, alpha: float = 0.5) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        """
        Hybrid Search using Reciprocal Rank Fusion (RRF).
        Currently implements RRF instead of Weighted Sum for robustness.
        
        Args:
            query_dense: Embedding vector
            query_text: Raw text for BM25
            k: Number of results
            alpha: Unused if RRF, but kept for signature compatibility
        """
        if not hasattr(self, 'bm25') or self.bm25 is None:
            self.build_bm25()

        # 1. Dense Search
        dense_indices, dense_scores, _ = self.search(query_dense, k=k*2) # Fetch more for fusion
        
        # 2. Sparse Search
        sparse_indices, sparse_scores = self.bm25.search(query_text, k=k*2)
        
        # 3. RRF Fusion
        # score = 1 / (rank + 60)
        rrf_scores = {}
        
        # Process Dense
        for rank, idx in enumerate(dense_indices):
            if idx not in rrf_scores: rrf_scores[idx] = 0
            rrf_scores[idx] += 1 / (rank + 60)
            
        # Process Sparse
        for rank, idx in enumerate(sparse_indices):
            if idx not in rrf_scores: rrf_scores[idx] = 0
            rrf_scores[idx] += 1 / (rank + 60)
            
        # Sort by RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)[:k]
        
        # Fetch metadata
        result_metadata = []
        final_scores = []
        for idx in sorted_indices:
            if 0 <= idx < len(self.metadata):
                result_metadata.append(self.metadata[idx])
                final_scores.append(rrf_scores[idx])
        
        return sorted_indices, final_scores, result_metadata
