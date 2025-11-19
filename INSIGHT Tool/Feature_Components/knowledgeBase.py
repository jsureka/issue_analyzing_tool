"""
Knowledge Base System - Main API for SPRINT integration
Provides bug localization using dense retrieval
"""

import logging
from typing import Dict, Any, Optional

from .KnowledgeBase.embedder import CodeEmbedder
from .KnowledgeBase.issue_processor import IssueProcessor
from .KnowledgeBase.retriever import DenseRetriever
from .KnowledgeBase.formatter import ResultFormatter
from .KnowledgeBase.indexer import RepositoryIndexer
from .KnowledgeBase.line_reranker import LineReranker
from .KnowledgeBase.calibrator import ConfidenceCalibrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances (lazy loaded)
_embedder = None
_issue_processor = None
_retriever = None
_formatter = None
_line_reranker = None
_calibrator = None


def _get_embedder(model_name: str = "microsoft/unixcoder-base") -> CodeEmbedder:
    """Get or create embedder instance"""
    global _embedder
    if _embedder is None:
        _embedder = CodeEmbedder(model_name)
        _embedder.load_model()
    return _embedder


def _get_issue_processor() -> IssueProcessor:
    """Get or create issue processor instance"""
    global _issue_processor
    if _issue_processor is None:
        embedder = _get_embedder()
        _issue_processor = IssueProcessor(embedder)
    return _issue_processor


def _get_retriever() -> DenseRetriever:
    """Get or create retriever instance"""
    global _retriever
    if _retriever is None:
        _retriever = DenseRetriever()
    return _retriever


def _get_formatter() -> ResultFormatter:
    """Get or create formatter instance"""
    global _formatter
    if _formatter is None:
        _formatter = ResultFormatter()
    return _formatter


def _get_line_reranker() -> LineReranker:
    """Get or create line reranker instance"""
    global _line_reranker
    if _line_reranker is None:
        _line_reranker = LineReranker()
    return _line_reranker


def _get_calibrator() -> ConfidenceCalibrator:
    """Get or create calibrator instance"""
    global _calibrator
    if _calibrator is None:
        _calibrator = ConfidenceCalibrator()
    return _calibrator


def BugLocalization(issue_title: str, issue_body: str, repo_owner: str, 
                   repo_name: str, repo_path: str, commit_sha: str = None,
                   k: int = 10, enable_line_level: bool = True) -> Dict[str, Any]:
    """
    Main API function for bug localization using Knowledge Base System
    
    Args:
        issue_title: GitHub issue title
        issue_body: GitHub issue body text
        repo_owner: Repository owner
        repo_name: Repository name
        repo_path: Local path to cloned repository
        k: Number of top results to return
        
    Returns:
        Dictionary with top files and functions, or error information
    """
    try:
        logger.info(f"Bug localization request for {repo_owner}/{repo_name}")
        
        # Construct full repo name
        full_repo_name = f"{repo_owner}/{repo_name}"
        
        # Get components
        retriever = _get_retriever()
        issue_processor = _get_issue_processor()
        formatter = _get_formatter()
        
        # Check if repository is indexed
        if not retriever.load_index(full_repo_name):
            error_msg = f"Repository {full_repo_name} is not indexed. Please index it first."
            logger.error(error_msg)
            return {
                'error': error_msg,
                'indexed': False,
                'repository': full_repo_name
            }
        
        # Process issue
        processed_issue = issue_processor.process_issue(issue_title, issue_body)
        if processed_issue is None:
            error_msg = "Failed to process issue text (too short or invalid)"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'repository': full_repo_name
            }
        
        logger.info(f"Processed issue: {processed_issue.word_count} words")
        
        # Retrieve similar functions
        results = retriever.retrieve(processed_issue.embedding, k=k)
        
        if not results:
            logger.warning("No results found")
            return {
                'repository': full_repo_name,
                'total_results': 0,
                'top_files': [],
                'message': 'No matching functions found'
            }
        
        # Phase 4: Calibrate confidence based on top score
        calibrator = _get_calibrator()
        top_score = results[0].similarity_score if results else 0.0
        overall_confidence, confidence_score = calibrator.calibrate_score(top_score)
        
        logger.info(f"Top score: {top_score:.3f} → {overall_confidence} confidence ({confidence_score:.2f})")
        
        # Get commit SHA
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
        
        # Phase 3: Line-level reranking (optional)
        line_results = None
        if enable_line_level:
            try:
                logger.info("Performing line-level reranking...")
                line_reranker = _get_line_reranker()
                
                # Load window index
                from pathlib import Path
                index_dir = Path("indices")
                window_index_path = index_dir / f"{full_repo_name.replace('/', '_')}_windows.index"
                window_metadata_path = index_dir / f"{full_repo_name.replace('/', '_')}_windows_metadata.json"
                
                if window_index_path.exists() and window_metadata_path.exists():
                    if line_reranker.load_window_index(full_repo_name, str(window_index_path), str(window_metadata_path)):
                        # Convert results to format expected by reranker
                        function_results = []
                        for result in results[:10]:  # Rerank top 10 functions
                            function_results.append({
                                'function_id': result.function_id,
                                'function_name': result.function_name,
                                'file_path': result.file_path,
                                'start_line': result.start_line,
                                'end_line': result.end_line,
                                'similarity_score': result.similarity_score,
                                'snippet': getattr(result, 'snippet', '')
                            })
                        
                        line_results = line_reranker.rerank_functions(processed_issue.embedding, function_results)
                        logger.info(f"Line-level reranking completed: {len(line_results)} results")
                else:
                    logger.info("Window index not found, skipping line-level reranking")
            except Exception as e:
                logger.warning(f"Line-level reranking failed: {e}")
        
        # Format results
        repo_info = {
            'repo_name': full_repo_name,
            'commit_sha': commit_sha
        }
        
        formatted_results = formatter.format_results(
            results,
            repo_info,
            repo_path=repo_path,
            top_n=5
        )
        
        # Add line-level results if available
        if line_results:
            formatted_results['line_level_results'] = [
                {
                    'function_name': lr.function_name,
                    'file_path': lr.file_path,
                    'line_start': lr.line_start,
                    'line_end': lr.line_end,
                    'snippet': lr.snippet,
                    'score': lr.similarity_score,
                    'confidence': lr.confidence
                }
                for lr in line_results[:5]  # Top 5 line-level results
            ]
        
        # Add confidence to results
        formatted_results['confidence'] = overall_confidence
        formatted_results['confidence_score'] = confidence_score
        
        logger.info(f"Successfully retrieved {len(results)} results with {overall_confidence} confidence")
        return formatted_results
        
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
