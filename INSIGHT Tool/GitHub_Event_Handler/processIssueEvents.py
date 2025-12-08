import logging
import time
import os
import subprocess
import tempfile
from config import Config as config
from .getCodeFiles import fetch_all_code_files
from .createCommentBugLocalization import CreateCommentBL, BLStartingCommentForWaiting, CreateErrorComment, CreateIndexingInProgressComment
from .app_authentication import authenticate_github_app
from Feature_Components.knowledgeBase import BugLocalization as KBBugLocalization, GetIndexStatus
from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger

logger = logging.getLogger(__name__)

def process_issue_event(repo_full_name, input_issue, action):
    start_time_total = time.time()
    
    try:    
        if action == 'opened':
            # Fetch code files from repository
            code_files = fetch_all_code_files(repo_full_name, input_issue['issue_branch'])
            paths_only = [file['path'] for file in code_files]

            # Prepare issue data
            input_issue_title = input_issue['issue_title'] or ""
            input_issue_body = input_issue['issue_body'] or ""

            # Get authentication token
            auth_token = authenticate_github_app(repo_full_name)

            # Bug localization using Knowledge Base System
            if paths_only:
                repo_owner, repo_name = repo_full_name.split('/')
                index_status = GetIndexStatus(repo_full_name)
                
                if index_status.get('indexed', False):
                    # Repository is indexed, proceed with analysis
                    BLStartingCommentForWaiting(repo_full_name, input_issue['issue_number'])
                    
                    # Use Knowledge Base system

                    # Sync repository to ensure files are present for snippet extraction
                    from .repository_sync import RepositorySync
                    
                    try:
                        sync = RepositorySync(config.REPO_STORAGE_PATH)
                        commit_sha = input_issue.get('commit_sha')
                        
                        # Sync repository (clones if missing, updates if present)
                        repo_path = sync.sync_repository(repo_full_name, commit_sha)
                        
                        # If commit_sha was not provided, get the one we synced to
                        if not commit_sha:
                            result = subprocess.run(
                                ['git', 'rev-parse', 'HEAD'],
                                cwd=repo_path,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0:
                                commit_sha = result.stdout.strip()
                                logger.info(f"Resolved commit SHA to {commit_sha}")
                            else:
                                logger.warning("Failed to resolve commit SHA after sync")
                                
                    except Exception as e:
                        logger.error(f"Failed to sync repository: {e}")
                        # Fallback to temp if sync fails
                        repo_path = os.path.join(tempfile.gettempdir(), 'insight_repos', repo_full_name)
                        commit_sha = None
                    
                    # Start timing for telemetry
                    start_time = time.time()
                    
                    kb_results = KBBugLocalization(
                        input_issue_title,
                        input_issue_body,
                        repo_owner,
                        repo_name,
                        repo_path,
                        commit_sha=commit_sha,
                        k=10,
                        default_branch=input_issue['issue_branch']
                    )
                    
                    # Calculate latency
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Log telemetry
                    telemetry = get_telemetry_logger()
                    
                    # Convert KB results to format expected by CreateCommentBL
                    if 'error' not in kb_results and kb_results.get('top_files'):
                        buggy_code_files_list = []
                        for file_result in kb_results['top_files']:
                            buggy_code_files_list.append({
                                'file': file_result['file_path'],
                                'score': file_result['score'],
                                'functions': file_result['functions']
                            })
                        
                        # Log successful retrieval
                        top_k = len(buggy_code_files_list)
                        confidence = kb_results.get('confidence', 'medium')
                        telemetry.log_retrieval(
                            issue_id=str(input_issue['issue_number']),
                            latency_ms=latency_ms,
                            top_k=top_k,
                            confidence=confidence,
                            repo_name=repo_full_name,
                            success=True
                        )
                    else:
                        # Fallback to empty list if KB fails
                        error_msg = kb_results.get('error', 'No results')
                        logger.warning(f"Knowledge Base retrieval failed or returned no results: {error_msg}")
                        buggy_code_files_list = []
                        
                        # Log failed retrieval
                        telemetry.log_retrieval(
                            issue_id=str(input_issue['issue_number']),
                            latency_ms=latency_ms,
                            top_k=0,
                            confidence='low',
                            repo_name=repo_full_name,
                            success=False
                        )
                        telemetry.log_error(
                            error_type='retrieval_failed',
                            error_msg=error_msg,
                            context={
                                'issue_number': input_issue['issue_number'],
                                'repo': repo_full_name
                            }
                        )
                        
                        # Notify user about the failure
                        CreateErrorComment(repo_full_name, input_issue['issue_number'], error_msg)
                else:
                    # Repository not indexed, return message
                    logger.info(f"Repository {repo_full_name} is not indexed. Skipping bug localization.")
                    CreateIndexingInProgressComment(repo_full_name, input_issue['issue_number'])
                    buggy_code_files_list = []
                
                if buggy_code_files_list:
                    CreateCommentBL(
                        repo_full_name, 
                        input_issue['issue_branch'], 
                        input_issue['issue_number'], 
                        buggy_code_files_list, 
                        paths_only,
                        kb_results=kb_results,
                        use_new_format=True
                    )
            
            # Log end-to-end latency
            total_latency_seconds = time.time() - start_time_total
            logger.info(f"End-to-end processing time: {total_latency_seconds:.2f}s")
            
            # Alert if latency exceeds threshold
            if total_latency_seconds > 10:
                logger.warning(f"⚠️ WARNING: End-to-end latency ({total_latency_seconds:.2f}s) exceeded 10 second threshold!")
                telemetry = get_telemetry_logger()
                telemetry.log_error(
                    error_type='latency_threshold_exceeded',
                    error_msg=f'End-to-end processing took {total_latency_seconds:.2f}s',
                    context={
                        'issue_number': input_issue['issue_number'],
                        'repo': repo_full_name,
                        'latency_seconds': total_latency_seconds
                    }
                )
        
        elif action == 'deleted':
            logger.info(f"Issue {input_issue['issue_number']} deleted (no action required since issues are not stored).")
    except Exception as e:
        logger.error(f"An error occurred in process_issue_event: {e}", exc_info=True)




