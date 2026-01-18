import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from Feature_Components.KnowledgeBase.incremental_indexer import IncrementalIndexer
from Feature_Components.KnowledgeBase.language_parser import FunctionInfo, ClassInfo

class TestIncrementalIndexer(unittest.TestCase):
    def setUp(self):
        # Create patchers
        self.p_graph = patch('Feature_Components.KnowledgeBase.incremental_indexer.GraphStore')
        self.p_vector = patch('Feature_Components.KnowledgeBase.incremental_indexer.VectorStore')
        self.p_embedder = patch('Feature_Components.KnowledgeBase.incremental_indexer.CodeEmbedder')
        self.p_parser = patch('Feature_Components.KnowledgeBase.incremental_indexer.ParserFactory')
        self.p_exists = patch('pathlib.Path.exists', return_value=True)

        # Start patchers
        self.mock_graph = self.p_graph.start()
        self.mock_vector = self.p_vector.start()
        self.mock_embedder = self.p_embedder.start()
        self.mock_parser = self.p_parser.start()
        self.mock_exists = self.p_exists.start()

        self.indexer = IncrementalIndexer("dummy_path")
        self.indexer.repo_name = "test_repo"
        
        # Mock vector store and embedder
        self.indexer.vector_store = MagicMock()
        self.indexer.vector_store.metadata = [] # List format
        self.indexer.embedder = MagicMock()
        self.indexer.embedder.embed_function.return_value = [0.1] * 768

    def tearDown(self):
        self.p_graph.stop()
        self.p_vector.stop()
        self.p_embedder.stop()
        self.p_parser.stop()
        self.p_exists.stop()

    def test_process_modified_files_metadata_list(self):
        """Test processing modified files with LIST metadata format"""
        # Mock metadata file containing a list
        mock_metadata = [
            {
                'id': 'test_repo::file.py::func::1',
                'file_path': 'file.py',
                'entity_type': 'function'
            },
            {
                'id': 'test_repo::other.py::func::1',
                'file_path': 'other.py',
                'entity_type': 'function'
            }
        ]
        
        with patch('builtins.open', unittest.mock.mock_open(read_data='[]')), \
             patch('json.load', return_value=mock_metadata), \
             patch.object(self.indexer, 'process_added_files') as mock_added:
            
            mock_added.return_value = ([], [], [])
            
            removed_ids, _, _, _ = self.indexer.process_modified_files(['file.py'])
            
            self.assertIn('test_repo::file.py::func::1', removed_ids)
            self.assertNotIn('test_repo::other.py::func::1', removed_ids)

    def test_update_faiss_index_skeletons(self):
        """Test that update_faiss_index calls embedder with skeletons"""
        # Mock inputs
        print(f"FunctionInfo module: {FunctionInfo.__module__}")
        try:
             import inspect
             print(f"FunctionInfo source: {inspect.getsource(FunctionInfo)}")
        except:
             print("Could not get source")

        info = FunctionInfo(name="main", signature="def main():", start_line=1, end_line=5, 
                        docstring=None, class_name=None, body="def main():\n    pass", language="python")
        print(f"DEBUG: Created info object: {info}")
        print(f"DEBUG: Has body? {hasattr(info, 'body')}")
        
        new_functions = [info]
        
        new_classes = [
            ClassInfo(name="MyClass", start_line=10, end_line=20, functions=["__init__"], 
                     language="python", docstring="Doc")
        ]
        
        new_files = [
            {
                'path': 'file.py',
                'source_code': 'import os\n\ndef main():\n    pass',
                'dataset': 'test',
                'functions': new_functions,
                'classes': new_classes,
                'language': 'python'
            }
        ]
        
        # We need to mock RepositoryIndexer.create_class_skeleton etc.
        # Since they are static, we can check if they are called indirectly by checking embedder input
        
        self.indexer.update_faiss_index([], new_functions, new_classes, new_files)
        
        # Verify embedder calls
        # 1. Function embed (full body)
        # 2. Class embed (skeleton)
        # 3. File embed (skeleton)
        
        calls = self.indexer.embedder.embed_function.call_args_list
        self.assertEqual(len(calls), 3)
        
        # Check Function call
        self.assertIn("def main():", calls[0][0][0]) 
        
        # Check Class call (should include docstring)
        self.assertIn('class MyClass:', calls[1][0][0])
        self.assertIn('"""Doc"""', calls[1][0][0])
        
        # Check File call (should include imports)
        self.assertIn('import os', calls[2][0][0])

if __name__ == '__main__':
    unittest.main()
