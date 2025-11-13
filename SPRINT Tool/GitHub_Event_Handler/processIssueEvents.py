from Issue_Indexer.getAllIssues import fetch_repository_issues
from .getCodeFiles import fetch_all_code_files
from Feature_Components.dupBRDetection import DuplicateDetection
from Feature_Components.BRSeverityPred import SeverityPrediction
from .createCommentBugLocalization import CreateCommentBL, BLStartingCommentForWaiting
from .createComment import create_comment, DupStartingCommentForWaiting
import multiprocessing
from functools import partial
from .app_authentication import authenticate_github_app
from .createComment import create_label
# Use new Knowledge Base system for bug localization
# from Feature_Components.bugLocalization import BugLocalization
from Feature_Components.knowledgeBase import BugLocalization as KBBugLocalization, GetIndexStatus
from Data_Storage.dbOperations import create_table_if_not_exists, is_table_exists, insert_issue_to_db, fetch_all_bug_reports_from_db, delete_issue_from_db
from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger
from Feature_Components.KnowledgeBase.auto_labeler import AutoLabeler

def process_issue_event(repo_full_name, input_issue, action):
    import time
    start_time_total = time.time()
    
    try:    
        if action == 'opened':
            if not is_table_exists(repo_full_name):
                print(f"Table for {repo_full_name} does not exist. Creating the table and fetching issues.")
                create_table_if_not_exists(repo_full_name)

                issues_data = fetch_repository_issues(repo_full_name)
                for issue in issues_data:

                    if issue['number'] == input_issue['issue_number']:
                        print(f"Skipping issue {issue['number']} as it matches the input issue title.")
                        continue  

                    issue_id = issue['number']
                    issue_title = issue['title'] or ""
                    issue_body = issue['body'] or ""
                    created_at = issue['created_at']  
                    issue_url = issue['html_url']  
                    issue_labels = [label['name'] for label in issue.get('labels', [])]

                    insert_issue_to_db(repo_full_name, issue_id, issue_title, issue_body, created_at, issue_url, issue_labels)
                issues_data = fetch_all_bug_reports_from_db(repo_full_name)
                if issues_data:
                    DupStartingCommentForWaiting(repo_full_name, input_issue['issue_number'])

            else:
                print(f"Table for {repo_full_name} already exists. Fetching issues from the database.")
                issues_data = fetch_all_bug_reports_from_db(repo_full_name)
                if issues_data:
                    DupStartingCommentForWaiting(repo_full_name, input_issue['issue_number'])


            code_files = fetch_all_code_files(repo_full_name, input_issue['issue_branch'])

            input_issue_title = input_issue['issue_title'] or ""
            input_issue_body = input_issue['issue_body'] or ""
            input_issue_data_for_model = input_issue_title + "\n" + input_issue_body

            issue_chunks = chunkify(issues_data, 4)
            
            pool = multiprocessing.Pool(processes=4)

            duplicate_detection_task = partial(process_issues_chunk, input_issue_data_for_model)
            results = pool.map(duplicate_detection_task, issue_chunks)

            pool.close()
            pool.join()

            duplicate_issue_list = [issue for result in results for issue in result]

            try:
                    insert_issue_to_db(
                        repo_full_name,
                        input_issue['issue_number'],
                        input_issue['issue_title'],
                        input_issue['issue_body'],
                        input_issue['created_at'],
                        input_issue['issue_url'],
                        input_issue['issue_labels']
                    )
                    
            except Exception as e:
                print(f"An error occurred while inserting the issue: {e}")

            auth_token = authenticate_github_app(repo_full_name)

            # Severity Prediction
            BRSeverity = SeverityPrediction(input_issue_data_for_model)
            create_label(repo_full_name, input_issue['issue_number'], BRSeverity, auth_token)

            if duplicate_issue_list:
                duplicate_issue_list = duplicate_issue_list[:10]
                create_comment(repo_full_name, input_issue['issue_number'], duplicate_issue_list)
            
            paths_only = [file['path'] for file in code_files]

            # Bug localization using Knowledge Base System
            if paths_only:
                BLStartingCommentForWaiting(repo_full_name, input_issue['issue_number'])
                
                # Check if repository is indexed
                repo_owner, repo_name = repo_full_name.split('/')
                index_status = GetIndexStatus(repo_full_name)
                
                if index_status.get('indexed', False):
                    # Use Knowledge Base system
                    # Get repository path from code_files fetch
                    import tempfile
                    import os
                    import time
                    repo_path = os.path.join(tempfile.gettempdir(), 'sprint_repos', repo_full_name)
                    
                    # Extract commit_sha from issue branch or use HEAD
                    commit_sha = input_issue.get('commit_sha', None)
                    if not commit_sha:
                        # Try to get commit SHA from repository
                        try:
                            import subprocess
                            result = subprocess.run(
                                ['git', 'rev-parse', 'HEAD'],
                                cwd=repo_path,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.returncode == 0:
                                commit_sha = result.stdout.strip()
                        except Exception as e:
                            print(f"Could not get commit SHA: {e}")
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
                        k=10
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
                        print(f"Knowledge Base retrieval failed or returned no results: {error_msg}")
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
                else:
                    # Repository not indexed, return message
                    print(f"Repository {repo_full_name} is not indexed. Skipping bug localization.")
                    buggy_code_files_list = []
                
                if buggy_code_files_list:
                    # Pass kb_results for new format comment generation
                    CreateCommentBL(
                        repo_full_name, 
                        input_issue['issue_branch'], 
                        input_issue['issue_number'], 
                        buggy_code_files_list, 
                        paths_only,
                        kb_results=kb_results,
                        use_new_format=True
                    )
                    
                    # Phase 4: Apply confidence label
                    try:
                        confidence = kb_results.get('confidence', 'medium')
                        auto_labeler = AutoLabeler(auth_token, repo_owner, repo_name)
                        
                        # Ensure labels exist
                        auto_labeler.ensure_labels_exist()
                        
                        # Apply confidence label
                        if auto_labeler.apply_confidence_label(input_issue['issue_number'], confidence):
                            logger.info(f"Applied {confidence} confidence label to issue #{input_issue['issue_number']}")
                        else:
                            logger.warning(f"Failed to apply confidence label to issue #{input_issue['issue_number']}")
                    except Exception as e:
                        logger.error(f"Auto-labeling failed: {e}")
            
            # Log end-to-end latency
            total_latency_seconds = time.time() - start_time_total
            print(f"End-to-end processing time: {total_latency_seconds:.2f}s")
            
            # Alert if latency exceeds threshold
            if total_latency_seconds > 10:
                print(f"⚠️ WARNING: End-to-end latency ({total_latency_seconds:.2f}s) exceeded 10 second threshold!")
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
            delete_issue_from_db(repo_full_name, input_issue['issue_number'])
            print(f"Deleted issue {input_issue['issue_number']} from the database.")
    except Exception as e:
        print(f"An error occurred in process_issue_event: {e}")




def chunkify(lst, n):
    return [lst[i::n] for i in range(n)]


def process_issues_chunk(input_issue_data_for_model, issues_chunk):
    duplicate_issue_list = []
    process_name = multiprocessing.current_process().name

    for issue in issues_chunk:
        issue_id = issue[0]     
        issue_title = issue[1]  
        issue_body = issue[2]
        issue_created = issue[3]    
        issue_url = issue[4]
        issue_labels = issue[5]

        issue_title = issue_title or ""
        issue_body = issue_body or ""
        issue_data_for_model = issue_title + "\n" + issue_body

        print(f"Process {process_name} is handling issue number {issue_id}")

        duplicatePrediction = DuplicateDetection(input_issue_data_for_model, issue_data_for_model, issue_id)

        if duplicatePrediction == [1]:
            duplicate_issue_list.append({
                "issue_id": issue_id,
                "issue_title": issue_title,
                "issue_created": issue_created,
                "issue_url": issue_url,
                "issue_label": issue_labels,
            })
    
    print(f"Process {process_name} processed {len(issues_chunk)} issues in total.")
    return duplicate_issue_list  