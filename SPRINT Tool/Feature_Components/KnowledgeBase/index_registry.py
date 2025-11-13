"""
Index Registry - Manages multiple versions of indices for historical retrieval
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class IndexRegistry:
    """Manages registry of all indexed versions for repositories"""
    
    def __init__(self, registry_path: str = "indices/index_registry.json"):
        """
        Initialize index registry
        
        Args:
            registry_path: Path to registry JSON file
        """
        self.registry_path = Path(registry_path)
        self.registries: Dict[str, Dict] = {}
        
        # Load existing registry
        if self.registry_path.exists():
            self.load_registry()
        
        logger.info(f"IndexRegistry initialized: {registry_path}")
    
    def load_registry(self) -> bool:
        """
        Load registry from file
        
        Returns:
            True if successful
        """
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.registries = data.get('repositories', {})
            
            logger.info(f"Loaded registry with {len(self.registries)} repositories")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return False
    
    def save_registry(self) -> bool:
        """
        Save registry to file
        
        Returns:
            True if successful
        """
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'last_updated': datetime.utcnow().isoformat() + 'Z',
                'repositories': self.registries
            }
            
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved registry with {len(self.registries)} repositories")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            return False
    
    def register_index(self, repo_name: str, commit_sha: str, 
                      index_info: Dict[str, Any]) -> bool:
        """
        Register a new index version
        
        Args:
            repo_name: Repository name
            commit_sha: Commit SHA
            index_info: Index information dictionary
            
        Returns:
            True if successful
        """
        try:
            if repo_name not in self.registries:
                self.registries[repo_name] = {
                    'repo': repo_name,
                    'indices': []
                }
            
            # Add index entry
            index_entry = {
                'commit_sha': commit_sha,
                'indexed_at': datetime.utcnow().isoformat() + 'Z',
                'index_path': index_info.get('index_path', ''),
                'window_index_path': index_info.get('window_index_path', ''),
                'metadata_path': index_info.get('metadata_path', ''),
                'is_delta': index_info.get('is_delta', False),
                'parent_commit': index_info.get('parent_commit', None),
                'size_mb': index_info.get('size_mb', 0),
                'total_functions': index_info.get('total_functions', 0),
                'total_windows': index_info.get('total_windows', 0)
            }
            
            # Check if commit already registered
            existing = [i for i in self.registries[repo_name]['indices'] 
                       if i['commit_sha'] == commit_sha]
            
            if existing:
                # Update existing entry
                idx = self.registries[repo_name]['indices'].index(existing[0])
                self.registries[repo_name]['indices'][idx] = index_entry
                logger.info(f"Updated index entry for {repo_name}@{commit_sha[:7]}")
            else:
                # Add new entry
                self.registries[repo_name]['indices'].append(index_entry)
                logger.info(f"Registered new index for {repo_name}@{commit_sha[:7]}")
            
            # Save registry
            return self.save_registry()
            
        except Exception as e:
            logger.error(f"Failed to register index: {e}")
            return False
    
    def get_index_info(self, repo_name: str, commit_sha: str = None) -> Optional[Dict[str, Any]]:
        """
        Get index information for a specific commit or latest
        
        Args:
            repo_name: Repository name
            commit_sha: Commit SHA (None for latest)
            
        Returns:
            Index information dictionary or None
        """
        if repo_name not in self.registries:
            return None
        
        indices = self.registries[repo_name]['indices']
        
        if not indices:
            return None
        
        if commit_sha:
            # Find specific commit
            for index in indices:
                if index['commit_sha'] == commit_sha:
                    return index
            return None
        else:
            # Return latest (last in list)
            return indices[-1]
    
    def list_indices(self, repo_name: str) -> List[Dict[str, Any]]:
        """
        List all indices for a repository
        
        Args:
            repo_name: Repository name
            
        Returns:
            List of index information dictionaries
        """
        if repo_name not in self.registries:
            return []
        
        return self.registries[repo_name]['indices']
    
    def delete_index(self, repo_name: str, commit_sha: str) -> bool:
        """
        Delete an index entry from registry
        
        Args:
            repo_name: Repository name
            commit_sha: Commit SHA
            
        Returns:
            True if successful
        """
        try:
            if repo_name not in self.registries:
                return False
            
            indices = self.registries[repo_name]['indices']
            
            # Find and remove
            for i, index in enumerate(indices):
                if index['commit_sha'] == commit_sha:
                    del indices[i]
                    logger.info(f"Deleted index entry for {repo_name}@{commit_sha[:7]}")
                    return self.save_registry()
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False
    
    def get_storage_stats(self, repo_name: str = None) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Args:
            repo_name: Repository name (None for all)
            
        Returns:
            Dictionary with storage statistics
        """
        if repo_name:
            if repo_name not in self.registries:
                return {'total_size_mb': 0, 'index_count': 0}
            
            indices = self.registries[repo_name]['indices']
            total_size = sum(i.get('size_mb', 0) for i in indices)
            
            return {
                'repo': repo_name,
                'total_size_mb': total_size,
                'index_count': len(indices),
                'indices': indices
            }
        else:
            # All repositories
            total_size = 0
            total_indices = 0
            
            for repo_data in self.registries.values():
                indices = repo_data['indices']
                total_size += sum(i.get('size_mb', 0) for i in indices)
                total_indices += len(indices)
            
            return {
                'total_size_mb': total_size,
                'total_indices': total_indices,
                'repository_count': len(self.registries)
            }
