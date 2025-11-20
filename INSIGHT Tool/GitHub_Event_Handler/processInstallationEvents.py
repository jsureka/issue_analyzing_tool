import logging
from Issue_Indexer.getAllIssues import fetch_repository_issues
from Data_Storage.dbOperations import insert_issue_to_db, create_table_if_not_exists, delete_table
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def process_installation_event(repo_full_name, repo_default_branch, action):
    """
    Process installation events (created/added) in background.
    """
    try:
        logger.info(f"Processing installation '{action}' for {repo_full_name}")
        
        if action in ['created', 'added']:
            create_table_if_not_exists(repo_full_name)
            issues_data = fetch_repository_issues(repo_full_name)
            
            for issue in issues_data:
                issue_id = issue['number']
                issue_title = issue['title'] or ""
                issue_body = issue['body'] or ""
                created_at = issue['created_at']
                issue_url = issue['html_url']  
                issue_labels = [label['name'] for label in issue.get('labels', [])]

                insert_issue_to_db(repo_full_name, issue_id, issue_title, issue_body, created_at, issue_url, issue_labels)
            
            # Trigger Knowledge Base indexing
            logger.info(f"Triggering Knowledge Base indexing for {repo_full_name}")
            
            # Lazy import to avoid potential circular dependency if any (though we are fixing them)
            from GitHub_Event_Handler.processPushEvents import process_push_event
            
            push_payload = {
                'repository': {
                    'full_name': repo_full_name,
                    'default_branch': repo_default_branch
                },
                'ref': f"refs/heads/{repo_default_branch}",
                'forced': False
            }
            process_push_event(repo_full_name, push_payload)
            
        elif action == 'deleted':
            delete_table(repo_full_name)
            logger.info(f"Deleted table for {repo_full_name}")

    except Exception as e:
        logger.error(f"Failed to process installation event for {repo_full_name}: {e}", exc_info=True)
