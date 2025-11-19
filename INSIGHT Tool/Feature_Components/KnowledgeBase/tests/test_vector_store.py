"""
Unit tests for FAISS vector store module
"""

import unittest
import tempfile
import os
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Feature_Components.KnowledgeBase.vector_store import VectorStore


class TestVectorStore(unittest.TestCase):
    """Test cases for VectorStore"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.vector_store = VectorStore(dimension=768)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_vector_store_initialization(self):
        """Test that vector store initializes correctly"""
        self.assertIsNotNone(self.vector_store)
        self.assertEqual(self.vector_store.dimension, 768)
        self.assertIsNone(self.vector_store.index)
        self.assertEqual(len(self.vector_store.metadata), 0)
    
    def test_create_index(self):
        """Test index creation"""
        self.vector_store.create_index()
        
        self.assertIsNotNone(self.vector_store.index)
        self.assertEqual(self.vector_store.index.ntotal, 0)  # Empty initially
    
    def test_add_vectors(self):
        """Test adding vectors to index"""
        self.vector_store.create_index()
        
        # Create test embeddings
        embeddings = np.random.randn(5, 768).astype(np.float32)
        # Normalize
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        metadata = [
            {'id': 'func1', 'name': 'function1', 'file_path': 'test.py'},
            {'id': 'func2', 'name': 'function2', 'file_path': 'test.py'},
            {'id': 'func3', 'name': 'function3', 'file_path': 'test.py'},
            {'id': 'func4', 'name': 'function4', 'file_path': 'test.py'},
            {'id': 'func5', 'name': 'function5', 'file_path': 'test.py'}
        ]
        
        success = self.vector_store.add_vectors(embeddings, metadata)
        
        self.assertTrue(success)
        self.assertEqual(self.vector_store.index.ntotal, 5)
        self.assertEqual(len(self.vector_store.metadata), 5)
    
    def test_add_vectors_mismatch(self):
        """Test that mismatched embeddings and metadata fails"""
        self.vector_store.create_index()
        
        embeddings = np.random.randn(3, 768).astype(np.float32)
        metadata = [{'id': 'func1'}, {'id': 'func2'}]  # Only 2 metadata
        
        success = self.vector_store.add_vectors(embeddings, metadata)
        
        self.assertFalse(success)
    
    def test_save_and_load_index(self):
        """Test saving and loading FAISS index"""
        self.vector_store.create_index()
        
        # Add some vectors
        embeddings = np.random.randn(3, 768).astype(np.float32)
        metadata = [
            {'id': 'func1', 'name': 'function1'},
            {'id': 'func2', 'name': 'function2'},
            {'id': 'func3', 'name': 'function3'}
        ]
        self.vector_store.add_vectors(embeddings, metadata)
        
        # Save index
        index_path = os.path.join(self.temp_dir, 'test_index.faiss')
        success = self.vector_store.save_index(index_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(index_path))
        
        # Load index in new vector store
        new_store = VectorStore(dimension=768)
        success = new_store.load_index(index_path)
        
        self.assertTrue(success)
        self.assertEqual(new_store.index.ntotal, 3)
    
    def test_save_and_load_metadata(self):
        """Test saving and loading metadata"""
        self.vector_store.create_index()
        
        metadata = [
            {'id': 'func1', 'name': 'function1', 'file_path': 'test.py'},
            {'id': 'func2', 'name': 'function2', 'file_path': 'test.py'}
        ]
        
        embeddings = np.random.randn(2, 768).astype(np.float32)
        self.vector_store.add_vectors(embeddings, metadata)
        
        # Save metadata
        metadata_path = os.path.join(self.temp_dir, 'test_metadata.json')
        success = self.vector_store.save_metadata(metadata_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(metadata_path))
        
        # Load metadata in new vector store
        new_store = VectorStore(dimension=768)
        success = new_store.load_metadata(metadata_path)
        
        self.assertTrue(success)
        self.assertEqual(len(new_store.metadata), 2)
        self.assertEqual(new_store.metadata[0]['name'], 'function1')
    
    def test_search(self):
        """Test similarity search"""
        self.vector_store.create_index()
        
        # Create test embeddings
        embeddings = np.random.randn(10, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        metadata = [{'id': f'func{i}', 'name': f'function{i}'} for i in range(10)]
        self.vector_store.add_vectors(embeddings, metadata)
        
        # Search with first embedding
        query = embeddings[0]
        indices, scores, result_metadata = self.vector_store.search(query, k=5)
        
        # Check results
        self.assertEqual(len(indices), 5)
        self.assertEqual(len(scores), 5)
        self.assertEqual(len(result_metadata), 5)
        
        # First result should be the query itself (highest similarity)
        self.assertEqual(indices[0], 0)
        self.assertGreater(scores[0], 0.9)  # Should be very high
    
    def test_search_with_k_larger_than_index(self):
        """Test search when k is larger than number of vectors"""
        self.vector_store.create_index()
        
        embeddings = np.random.randn(3, 768).astype(np.float32)
        metadata = [{'id': f'func{i}'} for i in range(3)]
        self.vector_store.add_vectors(embeddings, metadata)
        
        query = embeddings[0]
        indices, scores, result_metadata = self.vector_store.search(query, k=10)
        
        # Should return only 3 results
        self.assertEqual(len(indices), 3)
    
    def test_search_empty_index(self):
        """Test search on empty index"""
        self.vector_store.create_index()
        
        query = np.random.randn(768).astype(np.float32)
        indices, scores, result_metadata = self.vector_store.search(query, k=5)
        
        self.assertEqual(len(indices), 0)
        self.assertEqual(len(scores), 0)
        self.assertEqual(len(result_metadata), 0)
    
    def test_search_score_normalization(self):
        """Test that search scores are normalized to [0, 1]"""
        self.vector_store.create_index()
        
        embeddings = np.random.randn(5, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        metadata = [{'id': f'func{i}'} for i in range(5)]
        self.vector_store.add_vectors(embeddings, metadata)
        
        query = np.random.randn(768).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        indices, scores, result_metadata = self.vector_store.search(query, k=5)
        
        # All scores should be in [0, 1]
        for score in scores:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
    
    def test_get_stats(self):
        """Test getting vector store statistics"""
        self.vector_store.create_index()
        
        embeddings = np.random.randn(7, 768).astype(np.float32)
        metadata = [{'id': f'func{i}'} for i in range(7)]
        self.vector_store.add_vectors(embeddings, metadata)
        
        stats = self.vector_store.get_stats()
        
        self.assertEqual(stats['dimension'], 768)
        self.assertEqual(stats['total_vectors'], 7)
        self.assertEqual(stats['metadata_count'], 7)
    
    def test_metadata_index_field(self):
        """Test that metadata gets index field added"""
        self.vector_store.create_index()
        
        metadata = [
            {'id': 'func1', 'name': 'function1'},
            {'id': 'func2', 'name': 'function2'}
        ]
        embeddings = np.random.randn(2, 768).astype(np.float32)
        self.vector_store.add_vectors(embeddings, metadata)
        
        # Check that index field was added
        self.assertIn('index', self.vector_store.metadata[0])
        self.assertIn('index', self.vector_store.metadata[1])
        self.assertEqual(self.vector_store.metadata[0]['index'], 0)
        self.assertEqual(self.vector_store.metadata[1]['index'], 1)


if __name__ == '__main__':
    unittest.main()
