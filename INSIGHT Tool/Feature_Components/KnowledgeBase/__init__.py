"""
Knowledge Base System for SPRINT
Phase 1: Single-channel dense retrieval for bug localization
"""

__version__ = "1.0.0"

from .bug_localization import BugLocalization
from .indexer import RepositoryIndexer
from .index_registry import IndexRegistry
import os

def IndexRepository(repo_path, repo_name):
    """
    Helper function to index a repository.
    Returns: dict with 'success' (bool) and optional 'error' (str)
    """
    try:
        from ...config import Config
        indexer = RepositoryIndexer(Config.NEO4J_URI, Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        indexer.index_repository(repo_path, repo_name)
        # Register index
        registry = IndexRegistry()
        registry.register_index(repo_name, repo_path)
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def GetIndexStatus(repo_name):
    """
    Helper function to check if a repository is indexed.
    Returns: dict with 'indexed' (bool)
    """
    registry = IndexRegistry()
    # Check if index exists in registry or file system
    # For now, simple registry check
    # Or check if index dir exists
    # If using IndexRegistry:
    # return {'indexed': registry.get_index(repo_name) is not None}
    
    # Fallback/Direct check (assuming standard path structure from RepositoryIndexer)
    # This is a bit hacky but aligns with common patterns.
    # Ideally registry handles this.
    
    # If we don't have a reliable registry mechanism yet, let's verify file existence.
    # Config.KB_INDEX_DIR / repo_name_safe / index.faiss
    # But Config is in .config.
    
    # Prerequisite: We need Config.
    # Let's import Config properly.
    try:
        from ...config import Config
        index_dir = Config.KB_INDEX_DIR
        safe_name = repo_name.replace('/', '_')
        if os.path.exists(os.path.join(index_dir, safe_name, "index.faiss")):
             return {'indexed': True}
    except:
        pass
        
    return {'indexed': False}
