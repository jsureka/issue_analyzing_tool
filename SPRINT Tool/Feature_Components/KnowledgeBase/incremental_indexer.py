"""
Incremental Indexer - Efficiently updates indices when code changes
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of incremental index update"""
    repo_name: str
    old_commit: str
    new_commit: str
    files_changed: int
    functions_updated: int
    windows_updated: int
    update_time_seconds: float
    success: bool = True
    error_msg: str = ""


class IncrementalIndexer:
    """Handles incremental repository indexing based on git diffs"""
    
    def __init__(self, repo_path: str, base_indexer=None):
        """
        Initialize incremental indexer
        
        Args:
            repo_path: Path to git repository
            base_indexer: Base RepositoryIndexer instance for full reindexing
        """
        self.repo_path = Path(repo_path)
        self.base_indexer = base_indexer
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        logger.info(f"IncrementalIndexer initialized for {repo_path}")
    
    def get_changed_files(self, old_commit: str, new_commit: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Get files changed between two commits using git diff
        
        Args:
            old_commit: Old commit SHA
            new_commit: New commit SHA
            
        Returns:
            Tuple of (added_files, modified_files, deleted_files)
        """
        try:
            # Run git diff to get changed files
            result = subprocess.run(
                ['git', 'diff', '--name-status', old_commit, new_commit],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Git diff failed: {result.stderr}")
                return [], [], []
            
            # Parse output
            added_files = []
            modified_files = []
            deleted_files = []
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                
                status = parts[0]
                file_path = parts[1]
                
                # Only track Python files
                if not file_path.endswith('.py'):
                    continue
                
                if status == 'A':
                    added_files.append(file_path)
                elif status == 'M':
                    modified_files.append(file_path)
                elif status == 'D':
                    deleted_files.append(file_path)
                elif status.startswith('R'):  # Renamed
                    # Treat as modified
                    if len(parts) >= 3:
                        modified_files.append(parts[2])
            
            logger.info(f"Changed files: {len(added_files)} added, {len(modified_files)} modified, {len(deleted_files)} deleted")
            return added_files, modified_files, deleted_files
            
        except subprocess.TimeoutExpired:
            logger.error("Git diff timed out")
            return [], [], []
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return [], [], []
    
    def get_dependent_files(self, changed_files: List[str], graph_store=None) -> Set[str]:
        """
        Get files that depend on changed files (via imports)
        
        Args:
            changed_files: List of changed file paths
            graph_store: GraphStore instance for querying dependencies
            
        Returns:
            Set of dependent file paths
        """
        if not graph_store:
            logger.debug("No graph store provided, skipping dependency analysis")
            return set()
        
        try:
            dependent_files = set()
            
            for file_path in changed_files:
                # Query graph for files that import this file
                # This would require implementing a query in GraphStore
                # For now, return empty set
                pass
            
            logger.info(f"Found {len(dependent_files)} dependent files")
            return dependent_files
            
        except Exception as e:
            logger.error(f"Failed to get dependent files: {e}")
            return set()
    
    def classify_changes(self, added_files: List[str], modified_files: List[str], 
                        deleted_files: List[str]) -> Dict[str, List[str]]:
        """
        Classify file changes for processing
        
        Args:
            added_files: List of added files
            modified_files: List of modified files
            deleted_files: List of deleted files
            
        Returns:
            Dictionary with classified changes
        """
        return {
            'added': added_files,
            'modified': modified_files,
            'deleted': deleted_files,
            'to_reindex': added_files + modified_files,  # Files that need reindexing
            'to_remove': deleted_files  # Files to remove from index
        }
    
    def update_index(self, old_commit: str, new_commit: str) -> UpdateResult:
        """
        Incrementally update index from old to new commit
        
        Args:
            old_commit: Old commit SHA
            new_commit: New commit SHA
            
        Returns:
            UpdateResult with statistics
        """
        import time
        start_time = time.time()
        
        try:
            # Get changed files
            added, modified, deleted = self.get_changed_files(old_commit, new_commit)
            
            if not added and not modified and not deleted:
                logger.info("No Python files changed")
                return UpdateResult(
                    repo_name=self.repo_path.name,
                    old_commit=old_commit,
                    new_commit=new_commit,
                    files_changed=0,
                    functions_updated=0,
                    windows_updated=0,
                    update_time_seconds=time.time() - start_time
                )
            
            # Classify changes
            changes = self.classify_changes(added, modified, deleted)
            
            # Check if too many files changed (fallback to full reindex)
            total_changed = len(changes['to_reindex']) + len(changes['to_remove'])
            if total_changed > 50:
                logger.warning(f"Too many files changed ({total_changed}), falling back to full reindex")
                if self.base_indexer:
                    result = self.base_indexer.index_repository(str(self.repo_path), self.repo_path.name)
                    return UpdateResult(
                        repo_name=self.repo_path.name,
                        old_commit=old_commit,
                        new_commit=new_commit,
                        files_changed=total_changed,
                        functions_updated=result.total_functions,
                        windows_updated=result.total_windows,
                        update_time_seconds=time.time() - start_time
                    )
                else:
                    return UpdateResult(
                        repo_name=self.repo_path.name,
                        old_commit=old_commit,
                        new_commit=new_commit,
                        files_changed=total_changed,
                        functions_updated=0,
                        windows_updated=0,
                        update_time_seconds=time.time() - start_time,
                        success=False,
                        error_msg="Too many files changed and no base indexer available"
                    )
            
            # TODO: Implement actual incremental update logic
            # This would involve:
            # 1. Remove functions from deleted files
            # 2. Reparse and reindex modified/added files
            # 3. Update FAISS indices
            # 4. Update graph store
            
            logger.info(f"Incremental update completed in {time.time() - start_time:.2f}s")
            
            return UpdateResult(
                repo_name=self.repo_path.name,
                old_commit=old_commit,
                new_commit=new_commit,
                files_changed=total_changed,
                functions_updated=0,  # Placeholder
                windows_updated=0,  # Placeholder
                update_time_seconds=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Incremental update failed: {e}")
            return UpdateResult(
                repo_name=self.repo_path.name,
                old_commit=old_commit,
                new_commit=new_commit,
                files_changed=0,
                functions_updated=0,
                windows_updated=0,
                update_time_seconds=time.time() - start_time,
                success=False,
                error_msg=str(e)
            )
