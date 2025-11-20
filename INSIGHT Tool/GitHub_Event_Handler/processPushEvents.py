"""
Process GitHub push events for incremental knowledge base updates
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Import required components
from Feature_Components.KnowledgeBase.incremental_indexer import IncrementalIndexer
from Feature_Components.knowledgeBase import IndexRepository, GetIndexStatus
from Feature_Components.KnowledgeBase.update_metrics import UpdateMetrics
from Feature_Components.KnowledgeBase.update_config import UpdateConfig
from .repository_sync import RepositorySync, RepositorySyncError, GitOperationError


# Load configuration
config = UpdateConfig.from_env()
if not config.validate():
    logger.warning("Configuration validation failed, using defaults")

# Initialize metrics tracker
metrics_tracker = UpdateMetrics(config.metrics_storage_path)



def process_push_event(repo_full_name: str, push_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a GitHub push event and update the knowledge base
    
    Args:
        repo_full_name: Full repository name (owner/repo)
        push_payload: GitHub push event payload
        
    Returns:
        Dictionary with update results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing push event for {repo_full_name}")
        
        # Extract commit information
        before_commit = push_payload.get('before')
        after_commit = push_payload.get('after')
        commits = push_payload.get('commits', [])
        ref = push_payload.get('ref', '')
        
        # Validate branch (should already be filtered, but double-check)
        if not (ref.endswith('/main') or ref.endswith('/master')):
            logger.info(f"Skipping push to non-main branch: {ref}")
            return {
                'success': True,
                'skipped': True,
                'reason': 'non_main_branch',
                'branch': ref
            }
        
        # Get or sync repository
        # If after_commit is None (e.g. from installation event), sync to latest
        repo_path = get_or_sync_repository(repo_full_name, after_commit)
        
        # If after_commit was None, get the actual SHA we synced to
        if not after_commit:
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                after_commit = result.stdout.strip()
                logger.info(f"Resolved missing after_commit to {after_commit}")
            except Exception as e:
                logger.warning(f"Failed to resolve HEAD SHA: {e}")
                after_commit = "unknown"

        logger.info(
            f"Push event: {before_commit[:7] if before_commit else 'initial'} → "
            f"{after_commit[:7] if after_commit else 'unknown'} ({len(commits)} commits)"
        )
        
        # Check if repository is already indexed
        status = GetIndexStatus(repo_full_name)
        
        # Decide update strategy
        update_strategy = decide_update_strategy(
            status, 
            repo_full_name, 
            before_commit, 
            after_commit
        )
        
        logger.info(f"Update strategy: {update_strategy}")
        
        # Execute appropriate update
        if update_strategy == 'initial':
            # First time indexing - do full index
            result = execute_initial_index(repo_path, repo_full_name, after_commit)
        elif update_strategy == 'full':
            # Too many changes - do full re-index
            result = execute_full_reindex(repo_path, repo_full_name, after_commit)
        else:  # incremental
            # Incremental update
            result = execute_incremental_update(
                repo_path, 
                repo_full_name, 
                before_commit, 
                after_commit
            )
        
        # Add timing information
        result['total_time_seconds'] = time.time() - start_time
        
        # Log metrics
        metrics_tracker.log_update(result)
        
        logger.info(
            f"Push event processed successfully for {repo_full_name}: "
            f"{result.get('type', 'unknown')} update in {result['total_time_seconds']:.2f}s"
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to process push event for {repo_full_name}: {str(e)}"
        print(f"CRITICAL ERROR in process_push_event: {error_msg}") # Force output to terminal
        import traceback
        traceback.print_exc()
        logger.error(error_msg, exc_info=True)
        
        error_result = {
            'success': False,
            'error': error_msg,
            'repo_name': repo_full_name,
            'total_time_seconds': time.time() - start_time
        }
        
        # Log failed update metrics
        metrics_tracker.log_update(error_result)
        
        return error_result



def get_or_sync_repository(repo_full_name: str, commit_sha: str) -> str:
    """
    Get local repository path, syncing if necessary
    
    Args:
        repo_full_name: Full repository name (owner/repo)
        commit_sha: Commit SHA to sync to
        
    Returns:
        Local path to repository
        
    Raises:
        RepositorySyncError: If sync fails
    """
    try:
        sync = RepositorySync(config.repo_storage_path)
        repo_path = sync.sync_repository(
            repo_full_name, 
            commit_sha,
            max_retries=config.max_retries
        )
        logger.info(f"Repository synced: {repo_path}")
        return repo_path
    except (RepositorySyncError, GitOperationError) as e:
        logger.error(f"Failed to sync repository {repo_full_name}: {e}")
        raise



def decide_update_strategy(index_status: Dict[str, Any], repo_full_name: str,
                          before_commit: str, after_commit: str) -> str:
    """
    Decide whether to do initial, incremental, or full update
    
    Args:
        index_status: Current index status from GetIndexStatus
        repo_full_name: Repository name
        before_commit: Old commit SHA
        after_commit: New commit SHA
        
    Returns:
        Update strategy: 'initial', 'incremental', or 'full'
    """
    # Check if incremental updates are enabled
    if not config.incremental_update_enabled:
        logger.info("Incremental updates disabled, will perform full reindex")
        return 'full'
    
    # Check if repository is indexed
    if not index_status or not index_status.get('indexed'):
        logger.info(f"Repository {repo_full_name} not indexed, will perform initial indexing")
        return 'initial'
    
    # Get changed files to determine strategy
    try:
        sync = RepositorySync(config.repo_storage_path)
        added, modified, deleted = sync.get_changed_files(
            repo_full_name, 
            before_commit, 
            after_commit
        )
        
        total_changes = len(added) + len(modified) + len(deleted)
        
        if total_changes == 0:
            logger.info("No relevant files changed")
            return 'incremental'  # Will be a no-op
        
        if total_changes > config.max_files_for_incremental:
            logger.info(
                f"Too many files changed ({total_changes} > {config.max_files_for_incremental}), "
                f"will perform full reindex"
            )
            return 'full'
        
        logger.info(f"{total_changes} files changed, will perform incremental update")
        return 'incremental'
        
    except Exception as e:
        logger.warning(f"Failed to determine change count, defaulting to full reindex: {e}")
        return 'full'



def execute_initial_index(repo_path: str, repo_name: str, commit_sha: str) -> Dict[str, Any]:
    """
    Execute initial full indexing for a repository
    
    Args:
        repo_path: Local path to repository
        repo_name: Repository name
        commit_sha: Commit SHA being indexed
        
    Returns:
        Result dictionary
    """
    logger.info(f"Starting initial indexing for {repo_name}")
    
    try:
        result = IndexRepository(
            repo_path=repo_path,
            repo_name=repo_name
        )
        
        if result.get('success'):
            logger.info(
                f"Initial indexing complete for {repo_name}: "
                f"{result.get('total_functions', 0)} functions indexed"
            )
            return {
                'success': True,
                'type': 'initial',
                'repo_name': repo_name,
                'commit_sha': commit_sha,
                'total_functions': result.get('total_functions', 0),
                'total_files': result.get('total_files', 0),
                'indexing_time_seconds': result.get('indexing_time_seconds', 0)
            }
        else:
            raise Exception(result.get('error', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Initial indexing failed for {repo_name}: {e}", exc_info=True)
        return {
            'success': False,
            'type': 'initial',
            'error': str(e),
            'repo_name': repo_name
        }


def execute_full_reindex(repo_path: str, repo_name: str, commit_sha: str) -> Dict[str, Any]:
    """
    Execute full re-indexing for a repository
    
    Args:
        repo_path: Local path to repository
        repo_name: Repository name
        commit_sha: Commit SHA being indexed
        
    Returns:
        Result dictionary
    """
    logger.info(f"Starting full re-indexing for {repo_name}")
    
    try:
        result = IndexRepository(
            repo_path=repo_path,
            repo_name=repo_name
        )
        
        if result.get('success'):
            logger.info(
                f"Full re-indexing complete for {repo_name}: "
                f"{result.get('total_functions', 0)} functions indexed"
            )
            return {
                'success': True,
                'type': 'full_reindex',
                'repo_name': repo_name,
                'commit_sha': commit_sha,
                'total_functions': result.get('total_functions', 0),
                'total_files': result.get('total_files', 0),
                'indexing_time_seconds': result.get('indexing_time_seconds', 0)
            }
        else:
            raise Exception(result.get('error', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Full re-indexing failed for {repo_name}: {e}", exc_info=True)
        return {
            'success': False,
            'type': 'full_reindex',
            'error': str(e),
            'repo_name': repo_name
        }


def execute_incremental_update(repo_path: str, repo_name: str, 
                               before_commit: str, after_commit: str) -> Dict[str, Any]:
    """
    Execute incremental update for a repository
    
    Args:
        repo_path: Local path to repository
        repo_name: Repository name
        before_commit: Old commit SHA
        after_commit: New commit SHA
        
    Returns:
        Result dictionary
    """
    logger.info(f"Starting incremental update for {repo_name}")
    
    try:
        # Create incremental indexer
        indexer = IncrementalIndexer(repo_path, repo_name=repo_name)
        
        # Perform incremental update
        update_result = indexer.update_index(before_commit, after_commit)
        
        if update_result.success:
            logger.info(
                f"Incremental update complete for {repo_name}: "
                f"{update_result.functions_updated} functions updated in "
                f"{update_result.update_time_seconds:.2f}s"
            )
            return {
                'success': True,
                'type': 'incremental',
                'repo_name': repo_name,
                'old_commit': before_commit,
                'new_commit': after_commit,
                'files_changed': update_result.files_changed,
                'functions_updated': update_result.functions_updated,
                'update_time_seconds': update_result.update_time_seconds
            }
        else:
            # Incremental update failed, try full reindex as fallback
            logger.warning(
                f"Incremental update failed for {repo_name}: {update_result.error_msg}. "
                f"Falling back to full reindex"
            )
            return execute_full_reindex(repo_path, repo_name, after_commit)
            
    except Exception as e:
        logger.error(f"Incremental update failed for {repo_name}: {e}", exc_info=True)
        # Try full reindex as fallback
        logger.info(f"Attempting full reindex as fallback for {repo_name}")
        return execute_full_reindex(repo_path, repo_name, after_commit)
