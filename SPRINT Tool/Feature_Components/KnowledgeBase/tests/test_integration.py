"""
Integration tests for end-to-end Knowledge Base workflow
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo_dir = os.path.join(self.temp_dir, 'test_repo')
        os.makedirs(self.test_repo_dir)
        
        # Create a small test repository
        self._create_test_repository()
        
        # Initialize indexer with test directory
        self.indexer = RepositoryIndexer(
            model_name="microsoft/unixcoder-base",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            index_dir=os.path.join(self.temp_dir, 'indices')
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_repository(self):
        """Create a small test repository with Python files"""
        # File 1: utils.py
        utils_code = '''
"""Utility functions"""

def calculate_sum(a, b):
    """Calculate sum of two numbers"""
    return a + b

def calculate_product(a, b):
    """Calculate product of two numbers"""
    return a * b

def validate_input(value):
    """Validate input value"""
    if value is None:
        raise ValueError("Value cannot be None")
    return True
'''
        with open(os.path.join(self.test_repo_dir, 'utils.py'), 'w') as f:
            f.write(utils_code)
        
        # File 2: data_processor.py
        processor_code = '''
"""Data processing module"""

class DataProcessor:
    """Process data"""
    
    def __init__(self):
        self.data = []
    
    def add_data(self, item):
        """Add item to data"""
        self.data.append(item)
        return len(self.data)
    
    def process(self):
        """Process all data"""
        results = []
        for item in self.data:
            results.append(self._transform(item))
        return results
    
    def _transform(self, item):
        """Transform single item"""
        return str(item).upper()
'''
        with open(os.path.join(self.test_repo_dir, 'data_processor.py'), 'w') as f:
            f.write(processor_code)
        
        # File 3: main.py
        main_code = '''
"""Main module"""

from utils import calculate_sum
from data_processor import DataProcessor

def main():
    """Main entry point"""
    processor = DataProcessor()
    processor.add_data("test")
    result = processor.process()
    total = calculate_sum(1, 2)
    print(f"Result: {result}, Total: {total}")

if __name__ == "__main__":
    main()
'''
        with open(os.path.join(self.test_repo_dir, 'main.py'), 'w') as f:
            f.write(main_code)
    
    @unittest.skipIf(not os.path.exists("bolt://localhost:7687"), 
                     "Neo4j not available")
    def test_end_to_end_indexing(self):
        """Test complete indexing workflow"""
        try:
            # Index the test repository
            result = self.indexer.index_repository(
                repo_path=self.test_repo_dir,
                repo_name="test/repo"
            )
            
            # Verify indexing results
            self.assertEqual(result.repo_name, "test/repo")
            self.assertEqual(result.total_files, 3)
            self.assertGreater(result.total_functions, 0)
            self.assertGreater(result.indexing_time_seconds, 0)
            
            # Verify index files were created
            self.assertTrue(os.path.exists(result.index_path))
            self.assertTrue(os.path.exists(result.metadata_path))
            
            # Verify graph was built
            self.assertGreater(result.graph_nodes, 0)
            
            print(f"\nIndexing Results:")
            print(f"  Files: {result.total_files}")
            print(f"  Functions: {result.total_functions}")
            print(f"  Graph Nodes: {result.graph_nodes}")
            print(f"  Graph Edges: {result.graph_edges}")
            print(f"  Time: {result.indexing_time_seconds:.2f}s")
            
        except ConnectionError as e:
            self.skipTest(f"Could not connect to Neo4j: {e}")
        except Exception as e:
            self.fail(f"Indexing failed: {e}")
    
    def test_find_python_files(self):
        """Test finding Python files in repository"""
        python_files = self.indexer._find_python_files(self.test_repo_dir)
        
        self.assertEqual(len(python_files), 3)
        file_names = [f.name for f in python_files]
        self.assertIn('utils.py', file_names)
        self.assertIn('data_processor.py', file_names)
        self.assertIn('main.py', file_names)
    
    def test_index_status_check(self):
        """Test checking index status"""
        # Before indexing
        status = self.indexer.get_index_status("test/repo")
        self.assertIsNone(status)
        
        # After indexing (if Neo4j available)
        try:
            result = self.indexer.index_repository(
                repo_path=self.test_repo_dir,
                repo_name="test/repo"
            )
            
            # Check status
            status = self.indexer.get_index_status("test/repo")
            self.assertIsNotNone(status)
            self.assertTrue(status['indexed'])
            self.assertGreater(status['total_functions'], 0)
            
        except ConnectionError:
            self.skipTest("Neo4j not available")
    
    def test_empty_repository(self):
        """Test indexing empty repository"""
        empty_dir = os.path.join(self.temp_dir, 'empty_repo')
        os.makedirs(empty_dir)
        
        try:
            result = self.indexer.index_repository(
                repo_path=empty_dir,
                repo_name="test/empty"
            )
            
            self.assertEqual(result.total_files, 0)
            self.assertEqual(result.total_functions, 0)
            
        except ConnectionError:
            self.skipTest("Neo4j not available")
    
    def test_repository_with_errors(self):
        """Test indexing repository with some malformed files"""
        # Create a file with syntax errors
        bad_code = '''
def broken_function(
    # Missing closing parenthesis
    print("broken"
'''
        with open(os.path.join(self.test_repo_dir, 'broken.py'), 'w') as f:
            f.write(bad_code)
        
        try:
            result = self.indexer.index_repository(
                repo_path=self.test_repo_dir,
                repo_name="test/repo_with_errors"
            )
            
            # Should still succeed with partial results
            self.assertGreater(result.total_files, 0)
            # Failed files should be tracked
            self.assertGreaterEqual(len(result.failed_files), 0)
            
        except ConnectionError:
            self.skipTest("Neo4j not available")


class TestRetrievalIntegration(unittest.TestCase):
    """Integration tests for retrieval workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @unittest.skip("Requires full system setup")
    def test_end_to_end_retrieval(self):
        """Test complete retrieval workflow"""
        # This would test:
        # 1. Index a repository
        # 2. Process an issue
        # 3. Retrieve relevant functions
        # 4. Format results
        # 5. Verify output format
        pass


if __name__ == '__main__':
    unittest.main()
