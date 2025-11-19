"""
Repository Synchronization Manager
Handles cloning, updating, and syncing GitHub repositories locally
"""

import logging
import subprocess
import os
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Raised when git operations fail"""
    pass


class RepositorySyncError(Exception):
    """Raised when repository synchronization fails"""
    pass


class RepositorySync:
    """Manages local repository synchronization with GitHub"""
    
    def __init__(self, base_path: str = "Data_Storage/Repositories"):
        """
        Initialize repository sync manager
        
        Args:
            base_path: Base directory for storing repository clones
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"RepositorySync initialized with base path: {self.base_path}")
    
    def _get_repo_path(self, repo_full_name: str) -> Path:
        """
        Get local path for repository
        
        Args:
            repo_full_name: Repository name (e.g., "owner/repo")
            
        Returns:
            Path object for local repository
        """
        # Replace '/' with '_' to create valid directory name
        safe_name = repo_full_name.replace('/', '_')
        return self.base_path / safe_name
    
    def _run_git_command(self, command: List[str], cwd: Optional[Path] = None, 
                        timeout: int = 300) -> subprocess.CompletedProcess:
        """
        Run git command with error handling
        
        Args:
            command: Git command as list of strings
            cwd: Working directory for command
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess result
            
        Raises:
            GitOperationError: If git command fails
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                error_msg = f"Git command failed: {' '.join(command)}\nStderr: {result.stderr}"
                logger.error(error_msg)
                raise GitOperationError(error_msg)
            
            return result
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Git command timed out after {timeout}s: {' '.join(command)}"
            logger.error(error_msg)
            raise GitOperationError(error_msg) from e
        except Exception as e:
            error_msg = f"Git command error: {' '.join(command)}\nError: {str(e)}"
            logger.error(error_msg)
            raise GitOperationError(error_msg) from e

    
    def sync_repository(self, repo_full_name: str, commit_sha: Optional[str] = None, 
                       max_retries: int = 2) -> str:
        """
        Sync repository to latest commit or specific SHA
        
        Args:
            repo_full_name: Repository name (e.g., "owner/repo")
            commit_sha: Specific commit to sync to (optional, defaults to latest)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Local path to synced repository
            
        Raises:
            RepositorySyncError: If synchronization fails after retries
        """
        repo_path = self._get_repo_path(repo_full_name)
        
        for attempt in range(max_retries):
            try:
                if repo_path.exists():
                    # Repository exists, update it
                    logger.info(f"Updating existing repository: {repo_full_name}")
                    self._update_repository(repo_path, commit_sha)
                else:
                    # Clone repository
                    logger.info(f"Cloning repository: {repo_full_name}")
                    self._clone_repository(repo_full_name, repo_path, commit_sha)
                
                logger.info(f"Repository synced successfully: {repo_full_name} at {commit_sha or 'latest'}")
                return str(repo_path)
                
            except GitOperationError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Sync attempt {attempt + 1} failed, retrying: {e}")
                    # If update failed, try removing and cloning fresh
                    if repo_path.exists():
                        logger.info(f"Removing corrupted repository: {repo_path}")
                        import shutil
                        shutil.rmtree(repo_path, ignore_errors=True)
                else:
                    error_msg = f"Failed to sync repository {repo_full_name} after {max_retries} attempts"
                    logger.error(error_msg)
                    raise RepositorySyncError(error_msg) from e
        
        raise RepositorySyncError(f"Failed to sync repository {repo_full_name}")
    
    def _clone_repository(self, repo_full_name: str, repo_path: Path, 
                         commit_sha: Optional[str] = None):
        """
        Clone repository from GitHub
        
        Args:
            repo_full_name: Repository name (e.g., "owner/repo")
            repo_path: Local path to clone to
            commit_sha: Specific commit to checkout after cloning
        """
        clone_url = f"https://github.com/{repo_full_name}.git"
        
        # Clone repository
        self._run_git_command(['git', 'clone', clone_url, str(repo_path)])
        logger.info(f"Cloned repository to {repo_path}")
        
        # Checkout specific commit if provided
        if commit_sha:
            self._run_git_command(['git', 'checkout', commit_sha], cwd=repo_path)
            logger.info(f"Checked out commit {commit_sha}")
    
    def _update_repository(self, repo_path: Path, commit_sha: Optional[str] = None):
        """
        Update existing repository
        
        Args:
            repo_path: Local path to repository
            commit_sha: Specific commit to checkout
        """
        # Fetch latest changes
        self._run_git_command(['git', 'fetch', 'origin'], cwd=repo_path)
        logger.info(f"Fetched latest changes for {repo_path}")
        
        # Checkout specific commit or latest from default branch
        if commit_sha:
            self._run_git_command(['git', 'checkout', commit_sha], cwd=repo_path)
            logger.info(f"Checked out commit {commit_sha}")
        else:
            # Get default branch and checkout latest
            result = self._run_git_command(
                ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
                cwd=repo_path
            )
            default_branch = result.stdout.strip().replace('origin/', '')
            self._run_git_command(['git', 'checkout', default_branch], cwd=repo_path)
            self._run_git_command(['git', 'pull'], cwd=repo_path)
            logger.info(f"Updated to latest {default_branch}")

    
    def get_changed_files(self, repo_full_name: str, old_commit: str, 
                         new_commit: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Get files changed between two commits
        
        Args:
            repo_full_name: Repository name (e.g., "owner/repo")
            old_commit: Old commit SHA
            new_commit: New commit SHA
            
        Returns:
            Tuple of (added_files, modified_files, deleted_files)
            
        Raises:
            GitOperationError: If git diff fails
        """
        repo_path = self._get_repo_path(repo_full_name)
        
        if not repo_path.exists():
            raise RepositorySyncError(f"Repository not found: {repo_path}")
        
        try:
            # Run git diff to get changed files with status
            result = self._run_git_command(
                ['git', 'diff', '--name-status', old_commit, new_commit],
                cwd=repo_path,
                timeout=30
            )
            
            # Parse output
            added_files = []
            modified_files = []
            deleted_files = []
            
            # Supported file extensions
            supported_extensions = ('.py', '.java')
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                
                status = parts[0]
                file_path = parts[1]
                
                # Only track supported file types
                if not file_path.endswith(supported_extensions):
                    continue
                
                if status == 'A':
                    added_files.append(file_path)
                elif status == 'M':
                    modified_files.append(file_path)
                elif status == 'D':
                    deleted_files.append(file_path)
                elif status.startswith('R'):  # Renamed
                    # Treat renamed files as modified
                    if len(parts) >= 3:
                        new_path = parts[2]
                        if new_path.endswith(supported_extensions):
                            modified_files.append(new_path)
            
            logger.info(
                f"Changed files in {repo_full_name}: "
                f"{len(added_files)} added, {len(modified_files)} modified, "
                f"{len(deleted_files)} deleted"
            )
            
            return added_files, modified_files, deleted_files
            
        except GitOperationError as e:
            logger.error(f"Failed to get changed files: {e}")
            raise
