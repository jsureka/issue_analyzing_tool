
import unittest
import tempfile
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Mock dependencies before importing module
sys.modules['Data_Storage'] = MagicMock()
sys.modules['Data_Storage.dbOperations'] = MagicMock()
sys.modules['Issue_Indexer'] = MagicMock()
sys.modules['Issue_Indexer.getAllIssues'] = MagicMock()
sys.modules['Feature_Components'] = MagicMock()
sys.modules['Feature_Components.KnowledgeBase'] = MagicMock()
sys.modules['Feature_Components.KnowledgeBase.graph_store'] = MagicMock()

from GitHub_Event_Handler.processInstallationEvents import process_installation_event
from config import Config

class TestUninstallationCleanup(unittest.TestCase):
    """Verify that uninstallation cleans up all data"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_name = "test/cleanup_repo"
        
        # Mock Config paths
        self.original_repo_path = Config.REPO_STORAGE_PATH
        Config.REPO_STORAGE_PATH = os.path.join(self.temp_dir, 'insight_repos')
        
        # Create dummy repo files
        self.repo_dir = os.path.join(Config.REPO_STORAGE_PATH, self.repo_name)
        os.makedirs(self.repo_dir)
        with open(os.path.join(self.repo_dir, 'README.md'), 'w') as f:
            f.write("Test repo")
            
        # Create dummy index files
        self.index_dir = os.path.join(self.temp_dir, 'Data_Storage/KnowledgeBase')
        # Mock Config.KNOWLEDGE_BASE_DIR if it existed, but we can patch the module variable or rely on default
        # Since the code uses Config.KNOWLEDGE_BASE_DIR if available, let's mock it
        Config.KNOWLEDGE_BASE_DIR = self.index_dir
        
        self.repo_index_dir = os.path.join(self.index_dir, self.repo_name.replace('/', '_'))
        os.makedirs(self.repo_index_dir)
        with open(os.path.join(self.repo_index_dir, 'index.faiss'), 'w') as f:
            f.write("dummy index")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        Config.REPO_STORAGE_PATH = self.original_repo_path
        if hasattr(Config, 'KNOWLEDGE_BASE_DIR'):
            delattr(Config, 'KNOWLEDGE_BASE_DIR')

    @patch('GitHub_Event_Handler.processInstallationEvents.delete_table')
    @patch('GitHub_Event_Handler.processInstallationEvents.GraphStore')
    def test_cleanup_on_delete(self, mock_delete_table, mock_graph_store):
        """Test that 'deleted' action removes all files"""
        
        # Mock GraphStore
        mock_store_instance = MagicMock()
        mock_store_instance.connect.return_value = True
        mock_graph_store.return_value = mock_store_instance
        
        try:
            # Run the event handler
            process_installation_event(self.repo_name, "main", "deleted")
            
            # Verify DB cleanup
            mock_delete_table.assert_called_with(self.repo_name)
            
            # Verify Graph cleanup
            mock_store_instance.clear_database.assert_called_with(self.repo_name)
            
            # Verify Repo File cleanup
            self.assertFalse(os.path.exists(self.repo_dir), "Repo directory should be deleted")
            
            # Verify Index cleanup
            self.assertFalse(os.path.exists(self.repo_index_dir), "Index directory should be deleted")
            
            print("\nCleanup verification successful!")
        except Exception as e:
            print(f"\nTEST FAILED WITH ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise e

if __name__ == '__main__':
    unittest.main()
