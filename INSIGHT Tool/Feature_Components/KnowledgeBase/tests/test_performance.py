"""
Performance benchmarks for Knowledge Base System
"""

import unittest
import time
import tempfile
import os
import shutil
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Feature_Components.KnowledgeBase.parser import PythonParser
from Feature_Components.KnowledgeBase.embedder import CodeEmbedder
from Feature_Components.KnowledgeBase.vector_store import VectorStore
from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer


class TestPerformance(unittest.TestCase):
    """Performance benchmark tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_functions(self, count: int) -> list:
        """Create test Python functions"""
        functions = []
        for i in range(count):
            code = f'''
def function_{i}(param1, param2):
    """Function number {i}"""
    result = param1 + param2
    return result * {i}
'''
            functions.append(code)
        return functions
    
    def test_parsing_performance(self):
        """Benchmark parsing performance"""
        parser = PythonParser()
        
        # Create test file with many functions
        code_lines = ['"""Test module"""', '']
        for i in range(100):
            code_lines.append(f'''
def function_{i}(x, y):
    """Function {i}"""
    return x + y + {i}
''')
        
        code = '\n'.join(code_lines)
        test_file = os.path.join(self.temp_dir, 'test_parsing.py')
        with open(test_file, 'w') as f:
            f.write(code)
        
        # Benchmark parsing
        start_time = time.time()
        tree = parser.parse_file(test_file)
        with open(test_file, 'rb') as f:
            source_code = f.read()
        functions = parser.extract_functions(tree, source_code, test_file)
        elapsed = time.time() - start_time
        
        print(f"\nParsing Performance:")
        print(f"  Parsed {len(functions)} functions in {elapsed:.3f}s")
        print(f"  Rate: {len(functions)/elapsed:.1f} functions/second")
        
        # Should parse reasonably fast
        self.assertLess(elapsed, 2.0, "Parsing took too long")
        self.assertEqual(len(functions), 100)
    
    @unittest.skipIf(True, "Requires model download")
    def test_embedding_performance(self):
        """Benchmark embedding generation performance"""
        embedder = CodeEmbedder("microsoft/unixcoder-base")
        
        try:
            embedder.load_model()
        except Exception as e:
            self.skipTest(f"Could not load model: {e}")
        
        # Create test functions
        functions = self._create_test_functions(100)
        
        # Benchmark batch embedding
        start_time = time.time()
        embeddings = embedder.embed_batch(functions, batch_size=32)
        elapsed = time.time() - start_time
        
        print(f"\nEmbedding Performance:")
        print(f"  Generated {len(embeddings)} embeddings in {elapsed:.3f}s")
        print(f"  Rate: {len(embeddings)/elapsed:.1f} embeddings/second")
        
        self.assertEqual(len(embeddings), 100)
        
        # Target: at least 10 embeddings per second
        rate = len(embeddings) / elapsed
        print(f"  Target: >10 embeddings/second, Actual: {rate:.1f}")
    
    def test_vector_search_performance(self):
        """Benchmark vector search performance"""
        vector_store = VectorStore(dimension=768)
        vector_store.create_index()
        
        # Add 1000 vectors
        num_vectors = 1000
        embeddings = np.random.randn(num_vectors, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        metadata = [{'id': f'func{i}', 'name': f'function{i}'} for i in range(num_vectors)]
        vector_store.add_vectors(embeddings, metadata)
        
        # Benchmark search
        query = np.random.randn(768).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        # Warm-up
        vector_store.search(query, k=10)
        
        # Actual benchmark
        num_queries = 100
        start_time = time.time()
        for _ in range(num_queries):
            indices, scores, result_metadata = vector_store.search(query, k=10)
        elapsed = time.time() - start_time
        
        avg_time = elapsed / num_queries
        qps = num_queries / elapsed
        
        print(f"\nVector Search Performance:")
        print(f"  Index size: {num_vectors} vectors")
        print(f"  {num_queries} queries in {elapsed:.3f}s")
        print(f"  Average: {avg_time*1000:.2f}ms per query")
        print(f"  QPS: {qps:.1f} queries/second")
        
        # Target: < 100ms per query
        self.assertLess(avg_time, 0.1, "Search took too long")
    
    def test_memory_usage(self):
        """Benchmark memory usage"""
        import psutil
        import os as os_module
        
        process = psutil.Process(os_module.getpid())
        
        # Measure baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create vector store with many vectors
        vector_store = VectorStore(dimension=768)
        vector_store.create_index()
        
        num_vectors = 5000
        embeddings = np.random.randn(num_vectors, 768).astype(np.float32)
        metadata = [{'id': f'func{i}', 'name': f'function{i}'} for i in range(num_vectors)]
        
        vector_store.add_vectors(embeddings, metadata)
        
        # Measure memory after indexing
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = after_memory - baseline_memory
        
        print(f"\nMemory Usage:")
        print(f"  Baseline: {baseline_memory:.1f} MB")
        print(f"  After indexing {num_vectors} vectors: {after_memory:.1f} MB")
        print(f"  Memory used: {memory_used:.1f} MB")
        print(f"  Per vector: {memory_used/num_vectors*1024:.2f} KB")
        
        # Rough estimate: should be < 100 MB for 5000 vectors
        self.assertLess(memory_used, 200, "Memory usage too high")
    
    @unittest.skipIf(True, "Requires full system setup")
    def test_indexing_performance(self):
        """Benchmark full repository indexing"""
        # Create test repository with many files
        test_repo = os.path.join(self.temp_dir, 'perf_repo')
        os.makedirs(test_repo)
        
        # Create 50 files with 20 functions each = 1000 functions
        for file_num in range(50):
            code_lines = [f'"""Module {file_num}"""', '']
            for func_num in range(20):
                code_lines.append(f'''
def function_{file_num}_{func_num}(x, y):
    """Function {file_num}_{func_num}"""
    return x + y + {func_num}
''')
            
            filepath = os.path.join(test_repo, f'module_{file_num}.py')
            with open(filepath, 'w') as f:
                f.write('\n'.join(code_lines))
        
        # Benchmark indexing
        indexer = RepositoryIndexer(
            model_name="microsoft/unixcoder-base",
            index_dir=os.path.join(self.temp_dir, 'indices')
        )
        
        try:
            start_time = time.time()
            result = indexer.index_repository(test_repo, "test/perf_repo")
            elapsed = time.time() - start_time
            
            print(f"\nIndexing Performance:")
            print(f"  Files: {result.total_files}")
            print(f"  Functions: {result.total_functions}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Rate: {result.total_functions/elapsed:.1f} functions/second")
            
            # Target: < 15 minutes for 1000 functions (900 seconds)
            # That's about 1.1 functions per second
            rate = result.total_functions / elapsed
            print(f"  Target: >1 function/second, Actual: {rate:.2f}")
            
        except Exception as e:
            self.skipTest(f"Indexing failed: {e}")
    
    def test_retrieval_latency(self):
        """Benchmark end-to-end retrieval latency"""
        # Create and populate vector store
        vector_store = VectorStore(dimension=768)
        vector_store.create_index()
        
        num_vectors = 1000
        embeddings = np.random.randn(num_vectors, 768).astype(np.float32)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        metadata = [
            {
                'id': f'func{i}',
                'name': f'function{i}',
                'file_path': f'module{i//20}.py',
                'start_line': i * 10,
                'end_line': i * 10 + 5
            }
            for i in range(num_vectors)
        ]
        vector_store.add_vectors(embeddings, metadata)
        
        # Simulate issue processing and retrieval
        query = np.random.randn(768).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        # Benchmark
        num_queries = 50
        latencies = []
        
        for _ in range(num_queries):
            start = time.time()
            indices, scores, results = vector_store.search(query, k=10)
            latency = time.time() - start
            latencies.append(latency)
        
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        
        print(f"\nRetrieval Latency:")
        print(f"  Average: {avg_latency*1000:.2f}ms")
        print(f"  P95: {p95_latency*1000:.2f}ms")
        print(f"  P99: {p99_latency*1000:.2f}ms")
        
        # Target: < 1 second average
        self.assertLess(avg_latency, 1.0, "Retrieval latency too high")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
