import logging
from typing import List, Dict, Any, Tuple
import os

from .retriever import DenseRetriever
from .graph_store import GraphStore
from .llm_service import LLMService
from .issue_processor import IssueProcessor
from .embedder import CodeEmbedder

# Try to import Config from correct location
try:
    from ...config import Config
except ImportError:
    try:
        from config import Config
    except ImportError:
        # Fallback
        class Config:
            RETRIEVER_TOP_K = 20
            LLM_SELECTION_COUNT = 3

logger = logging.getLogger(__name__)

class BugLocalization:
    """
    RAG pipeline for bug localization.
    Retrieves top-k functions via dense vector search, enriches with graph context,
    and uses LLM to select the most likely buggy functions.
    """
    
    def __init__(self, repo_name: str, repo_path: str):
        self.repo_name = repo_name
        self.repo_path = repo_path
        
        # Initialize components
        self.embedder = CodeEmbedder()
        if not self.embedder.model:
            self.embedder.load_model()
            
        self.issue_processor = IssueProcessor(self.embedder)
        
        self.retriever = DenseRetriever()
        self.retriever.load_index(repo_name)
        
        self.graph_store = GraphStore()
        self.graph_store.connect()
        
        self.llm_service = LLMService()
        
    def localize(self, issue_title: str, issue_body: str, k: int = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Localize buggy functions for an issue.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            k: Number of candidates to retrieve (defaults to Config.RETRIEVER_TOP_K)
            
        Returns:
            Tuple[List[Dict], List[Dict], Dict]: (Final Ranked Candidates, Initial Retrieved Candidates, Token Usage)
        """
        if k is None:
            k = Config.RETRIEVER_TOP_K
            
        logger.info(f"Starting bug localization for: {issue_title}")
        
        # 1. Process Issue
        processed_issue = self.issue_processor.process_issue(issue_title, issue_body)
        
        # 1.5 Generate Smart Search Query
        search_query = self.llm_service.generate_search_query(issue_title, issue_body)
        logger.info(f"Generated search query: {search_query}")
        
        # Embed the query instead of the raw issue
        query_embedding = self.embedder.embed_function(search_query, None, "", 512)
        
        # 2. Retrieve Candidates
        retrieval_results = self.retriever.retrieve(query_embedding, k=k)
        if not retrieval_results:
            logger.warning("No candidates retrieved.")
            return [], [], {}
            
        # 3. Enrich Candidates with Graph Context & Code
        candidates = self._enrich_candidates(retrieval_results)
        
        # 4. LLM Selection (Re-ranking)
        logger.info(f"Selecting from {len(candidates)} candidates...")
        try:
            selected_funcs, token_usage = self.llm_service.select_functions(issue_title, issue_body, candidates)
        except Exception as e:
            logger.error(f"LLM selection failed: {e}")
            # Fallback: Use retriever order
            return candidates[:Config.LLM_SELECTION_COUNT], candidates, {}

        # Limit to configured number of selected functions
        selected_funcs = selected_funcs[:Config.LLM_SELECTION_COUNT]

        # Construct Final Ranked List
        # 1. LLM Selected (Top Priority)
        final_ranked_list = []
        selected_ids = set()
        
        for func in selected_funcs:
            final_ranked_list.append(func)
            selected_ids.add(func['id'])
            
        # 2. Remaining Candidates (Retriever Order)
        for cand in candidates:
            if cand['id'] not in selected_ids:
                final_ranked_list.append(cand)
                
        return final_ranked_list, candidates, token_usage

    def _enrich_candidates(self, retrieval_results) -> List[Dict[str, Any]]:
        """Enrich retrieval results with code and graph context."""
        candidates = []
        entity_ids = [r.id for r in retrieval_results]
        
        # Batch fetch graph neighbors
        neighbors_map = self.graph_store.get_function_neighbors(entity_ids)
        
        for res in retrieval_results:
            cand = {
                'id': res.id,
                'entity_type': res.entity_type,
                'name': res.name,
                'file_path': res.file_path,
                'class_name': res.class_name,
                'score': res.similarity_score,
                'signature': res.signature,
                'docstring': res.docstring
            }
            
            # 1. Get Code
            # Try to read from file first, fallback to snippet from vector store
            code_content = ""
            try:
                full_path = os.path.join(self.repo_path, res.file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        if res.entity_type == 'file':
                             code_content = f.read() # Read whole file for 'file' type
                        else:
                            lines = f.readlines()
                            start = max(0, res.start_line - 1)
                            end = min(len(lines), res.end_line)
                            code_content = "".join(lines[start:end])
            except Exception as e:
                logger.warning(f"Could not read code for {res.name}: {e}")
            
            if not code_content:
                # Fallback
                code_content = (res.docstring or "") + "\n" + res.signature
                
            cand['code'] = code_content
            
            # 2. Get Graph Neighbors
            neighbors = neighbors_map.get(res.id, {})
            cand['callers'] = neighbors.get('callers', [])
            cand['callees'] = neighbors.get('callees', [])
            
            candidates.append(cand)
            
        return candidates
