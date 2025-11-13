"""
Unit tests for code embedder module
"""

import unittest
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Feature_Components.KnowledgeBase.embedder import CodeEmbedder


class TestCodeEmbedder(unittest.TestCase):
    """Test cases for CodeEmbedder"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        # Use a small model for testing
        cls.embedder = CodeEmbedder(model_name="microsoft/unixcoder-base")
        # Load model once for all tests
        try:
            cls.embedder.load_model()
            cls.model_available = True
        except Exception as e:
            print(f"Warning: Could not load model: {e}")
            cls.model_available = False
    
    def test_embedder_initialization(self):
        """Test that embedder initializes correctly"""
        embedder = CodeEmbedder()
        self.assertIsNotNone(embedder)
        self.assertEqual(embedder.model_name, "microsoft/unixcoder-base")
    
    def test_device_detection(self):
        """Test device detection (CPU/GPU)"""
        device = self.embedder._get_device()
        self.assertIn(device, ['cpu', 'cuda'])
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_model_loading(self):
        """Test model loading"""
        self.assertIsNotNone(self.embedder.model)
        self.assertIsNotNone(self.embedder.tokenizer)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_embed_function(self):
        """Test embedding generation for a single function"""
        signature = "def calculate_sum(a, b):"
        docstring = "Calculate the sum of two numbers"
        body = "def calculate_sum(a, b):\n    return a + b"
        
        embedding = self.embedder.embed_function(signature, docstring, body)
        
        # Check embedding properties
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (768,))  # UniXcoder dimension
        self.assertEqual(embedding.dtype, np.float32)
        
        # Check normalization (L2 norm should be ~1)
        norm = np.linalg.norm(embedding)
        self.assertAlmostEqual(norm, 1.0, places=5)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_embed_function_without_docstring(self):
        """Test embedding generation without docstring"""
        signature = "def simple_function():"
        body = "def simple_function():\n    pass"
        
        embedding = self.embedder.embed_function(signature, None, body)
        
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (768,))
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_embed_batch(self):
        """Test batch embedding generation"""
        texts = [
            "def func1():\n    return 1",
            "def func2():\n    return 2",
            "def func3():\n    return 3"
        ]
        
        embeddings = self.embedder.embed_batch(texts, batch_size=2)
        
        # Check batch properties
        self.assertIsInstance(embeddings, np.ndarray)
        self.assertEqual(embeddings.shape, (3, 768))
        self.assertEqual(embeddings.dtype, np.float32)
        
        # Check each embedding is normalized
        for i in range(3):
            norm = np.linalg.norm(embeddings[i])
            self.assertAlmostEqual(norm, 1.0, places=5)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_embed_batch_empty(self):
        """Test batch embedding with empty list"""
        embeddings = self.embedder.embed_batch([])
        self.assertEqual(len(embeddings), 0)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_embed_issue(self):
        """Test issue embedding generation"""
        title = "Bug in login function"
        body = "The login function fails when username contains special characters"
        
        embedding = self.embedder.embed_issue(title, body)
        
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (768,))
        
        # Check normalization
        norm = np.linalg.norm(embedding)
        self.assertAlmostEqual(norm, 1.0, places=5)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_embedding_similarity(self):
        """Test that similar code produces similar embeddings"""
        code1 = "def add(a, b):\n    return a + b"
        code2 = "def sum_numbers(x, y):\n    return x + y"
        code3 = "def multiply(a, b):\n    return a * b"
        
        emb1 = self.embedder.embed_function("", None, code1)
        emb2 = self.embedder.embed_function("", None, code2)
        emb3 = self.embedder.embed_function("", None, code3)
        
        # Cosine similarity between add functions should be higher
        sim_12 = np.dot(emb1, emb2)
        sim_13 = np.dot(emb1, emb3)
        
        # add and sum should be more similar than add and multiply
        self.assertGreater(sim_12, sim_13)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_model_caching(self):
        """Test that model is cached and reused"""
        embedder1 = CodeEmbedder("microsoft/unixcoder-base")
        embedder1.load_model()
        
        embedder2 = CodeEmbedder("microsoft/unixcoder-base")
        embedder2.load_model()
        
        # Both should reference the same cached model
        self.assertIs(embedder1.model, embedder2.model)
    
    @unittest.skipIf(not hasattr(setUpClass, 'model_available') or not TestCodeEmbedder.model_available,
                     "Model not available")
    def test_long_code_truncation(self):
        """Test that very long code is handled properly"""
        # Create very long code
        long_code = "def long_function():\n" + "    x = 1\n" * 1000
        
        embedding = self.embedder.embed_function("", None, long_code)
        
        # Should still produce valid embedding
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (768,))


if __name__ == '__main__':
    unittest.main()
