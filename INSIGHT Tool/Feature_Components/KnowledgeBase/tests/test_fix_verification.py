
import unittest
import tempfile
import os
import shutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer

class TestFixVerification(unittest.TestCase):
    """Verify that the indexer fix restores Phase 3 (Window Embeddings)"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo_dir = os.path.join(self.temp_dir, 'test_repo')
        os.makedirs(self.test_repo_dir)
        
        # Create a dummy file large enough to have windows
        with open(os.path.join(self.test_repo_dir, 'large_file.py'), 'w') as f:
            f.write('def large_function():\n')
            for i in range(100):
                f.write(f'    print("Line {i}")\n')
        
        self.indexer = RepositoryIndexer(
            model_name="microsoft/unixcoder-base",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            index_dir=os.path.join(self.temp_dir, 'indices')
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_window_indexing_restored(self):
        """Test that window indices are created"""
        try:
            result = self.indexer.index_repository(
                repo_path=self.test_repo_dir,
                repo_name="test/fix_verification"
            )
            
            print(f"\nTotal Windows Generated: {result.total_windows}")
            
            # 1. Verify total_windows is populated (was 0 in broken version)
            self.assertGreater(result.total_windows, 0, "Total windows should be > 0")
            
            # 2. Verify window index files exist
            self.assertTrue(os.path.exists(result.window_index_path), "Window index file missing")
            
            # 3. Verify status check includes window info
            status = self.indexer.get_index_status("test/fix_verification")
            self.assertIsNotNone(status)
            self.assertIn('window_index_path', status)
            self.assertIsNotNone(status['window_index_path'])
            
        except ConnectionError:
            print("Skipping test: Neo4j not available")
        except Exception as e:
            self.fail(f"Test failed with error: {e}")

if __name__ == '__main__':
    unittest.main()
