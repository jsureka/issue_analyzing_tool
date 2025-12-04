import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def process_installation_event(repo_full_name, repo_default_branch, action):
    """
    Process installation events (created/added) in background.
    """
    try:
        logger.info(f"Processing installation '{action}' for {repo_full_name}")
        
        if action in ['created', 'added']:
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
            # 1. Delete Neo4j data
            try:
                from Feature_Components.KnowledgeBase.graph_store import GraphStore
                store = GraphStore()
                if store.connect():
                    store.clear_database(repo_full_name)
                    store.close()
                    logger.info(f"Cleared Neo4j graph for {repo_full_name}")
            except Exception as e:
                logger.error(f"Failed to clear Neo4j data: {e}")
                
            # 2. Delete Vector Index files
            try:
                import shutil
                import os
                from config import Config
                
                # Construct path (assuming default structure from indexer.py)
                index_dir = Config.KNOWLEDGE_BASE_DIR if hasattr(Config, 'KNOWLEDGE_BASE_DIR') else "Data_Storage/KnowledgeBase"
                repo_dir = os.path.join(index_dir, repo_full_name.replace('/', '_'))
                
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir)
                    logger.info(f"Deleted vector index directory: {repo_dir}")
                    
                # 3. Delete Cloned Repository Files
                repo_storage_path = Config.REPO_STORAGE_PATH
                cloned_repo_dir = os.path.join(repo_storage_path, repo_full_name)
                
                if os.path.exists(cloned_repo_dir):
                    shutil.rmtree(cloned_repo_dir)
                    logger.info(f"Deleted cloned repository files: {cloned_repo_dir}")
                    
            except Exception as e:
                logger.error(f"Failed to delete local files: {e}")

    except Exception as e:
        logger.error(f"Failed to process installation event for {repo_full_name}: {e}", exc_info=True)
