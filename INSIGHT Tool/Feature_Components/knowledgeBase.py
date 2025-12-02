"""
Knowledge Base System - Main API for SPRINT integration
Provides bug localization using dense retrieval and LangGraph workflow
"""

import logging
import threading
from typing import Dict, Any, Optional

from .KnowledgeBase.embedder import CodeEmbedder
from .KnowledgeBase.issue_processor import IssueProcessor
from .KnowledgeBase.retriever import DenseRetriever
from .KnowledgeBase.formatter import ResultFormatter
from .KnowledgeBase.indexer import RepositoryIndexer
from .KnowledgeBase.graph_store import GraphStore
from .KnowledgeBase.llm_service import LLMService


from .KnowledgeBase.workflow_manager import WorkflowManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances (lazy loaded) with locks
_embedder = None
_embedder_lock = threading.Lock()

_issue_processor = None
_issue_processor_lock = threading.Lock()

_retriever = None
_retriever_lock = threading.Lock()

_formatter = None
_formatter_lock = threading.Lock()






def _get_embedder(model_name: str = "microsoft/unixcoder-base") -> CodeEmbedder:
    """Get or create embedder instance (Thread-Safe)"""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                _embedder = CodeEmbedder(model_name)
                _embedder.load_model()
    return _embedder


def _get_issue_processor() -> IssueProcessor:
    """Get or create issue processor instance (Thread-Safe)"""
    global _issue_processor
    if _issue_processor is None:
        with _issue_processor_lock:
            if _issue_processor is None:
                embedder = _get_embedder()
                _issue_processor = IssueProcessor(embedder)
    return _issue_processor


def _get_retriever() -> DenseRetriever:
    """Get or create retriever instance (Thread-Safe)"""
    global _retriever
    if _retriever is None:
        with _retriever_lock:
            if _retriever is None:
                _retriever = DenseRetriever()
    return _retriever


def _get_formatter() -> ResultFormatter:
    """Get or create formatter instance (Thread-Safe)"""
    global _formatter
    if _formatter is None:
        with _formatter_lock:
            if _formatter is None:
                _formatter = ResultFormatter()
    return _formatter








def BugLocalization(issue_title: str, issue_body: str, repo_owner: str, 
                   repo_name: str, repo_path: str, commit_sha: str = None,
                   k: int = 10, enable_line_level: bool = True,
                   default_branch: str = 'main') -> Dict[str, Any]:
    """
    Main API function for bug localization using Knowledge Base System
    
    Args:
        issue_title: GitHub issue title
        issue_body: GitHub issue body text
        repo_owner: Repository owner
        repo_name: Repository name
        repo_path: Local path to cloned repository
        k: Number of top results to return
        default_branch: Default branch name for GitHub links
        
    Returns:
        Dictionary with top files and functions, or error information
    """
    try:
        logger.info(f"Bug localization request for {repo_owner}/{repo_name}")
        
        # Construct full repo name
        full_repo_name = f"{repo_owner}/{repo_name}"
        
        # Get components
        retriever = _get_retriever()
        
        # Check if repository is indexed
        if not retriever.load_index(full_repo_name):
            error_msg = f"Repository {full_repo_name} is not indexed. Please index it first."
            logger.error(error_msg)
            return {
                'error': error_msg,
                'indexed': False,
                'repository': full_repo_name
            }
            
        # Phase 2: Use LangGraph Workflow
        try:
            logger.info("Starting LangGraph Workflow...")
            workflow_manager = WorkflowManager()
            workflow_result = workflow_manager.run(
                issue_title, 
                issue_body, 
                full_repo_name, 
                repo_path
            )
            
            # Get commit SHA (if not already in result)
            import subprocess
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
            except:
                commit_sha = "unknown"
                
            workflow_result['commit_sha'] = commit_sha
            workflow_result['branch'] = default_branch
            
            # Add confidence info (using calibrator on top result if available)
            # if workflow_result.get('top_files'):
            #     top_score = workflow_result['top_files'][0].get('score', 0.0)
            #     calibrator = _get_calibrator()
            #     overall_confidence, confidence_score = calibrator.calibrate_score(top_score)
            #     workflow_result['confidence_level'] = overall_confidence
            #     workflow_result['confidence_score'] = confidence_score
            pass
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}", exc_info=True)
            return {
                'error': f"Workflow failed: {str(e)}",
                'repository': full_repo_name
            }
        
    except Exception as e:
        logger.error(f"Bug localization failed: {e}", exc_info=True)
        return {
            'error': str(e),
            'repository': f"{repo_owner}/{repo_name}"
        }


def IndexRepository(repo_path: str, repo_name: str, 
                   model_name: str = "microsoft/unixcoder-base",
                   neo4j_uri: str = "bolt://localhost:7687",
                   neo4j_user: str = "neo4j",
                   neo4j_password: str = "password") -> Dict[str, Any]:
    """
    Index a repository for bug localization
    
    Args:
        repo_path: Path to repository root
        repo_name: Repository name (e.g., "owner/repo")
        model_name: Embedding model name
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        
    Returns:
        Dictionary with indexing results and statistics
    """
    try:
        logger.info(f"Starting indexing for repository: {repo_name}")
        
        # Create indexer
        indexer = RepositoryIndexer(
            model_name=model_name,
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password
        )
        
        # Index repository
        result = indexer.index_repository(repo_path, repo_name)
        
        # Convert to dictionary
        return {
            'success': True,
            'repo_name': result.repo_name,
            'commit_sha': result.commit_sha,
            'total_files': result.total_files,
            'total_functions': result.total_functions,
            'index_path': result.index_path,
            'metadata_path': result.metadata_path,
            'graph_nodes': result.graph_nodes,
            'graph_edges': result.graph_edges,
            'indexing_time_seconds': result.indexing_time_seconds,
            'failed_files': result.failed_files
        }
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'repo_name': repo_name
        }


def GetIndexStatus(repo_name: str) -> Dict[str, Any]:
    """
    Check if a repository is indexed
    
    Args:
        repo_name: Repository name (e.g., "owner/repo")
        
    Returns:
        Dictionary with index status
    """
    try:
        indexer = RepositoryIndexer()
        status = indexer.get_index_status(repo_name)
        
        if status is None:
            return {
                'indexed': False,
                'repo_name': repo_name,
                'message': 'Repository not indexed'
            }
        
        return {
            'indexed': True,
            'repo_name': repo_name,
            **status
        }
        
    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        return {
            'indexed': False,
            'repo_name': repo_name,
            'error': str(e)
        }
