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
        query_result = self.llm_service.generate_search_query(issue_title, issue_body)
        
        search_query = query_result.get("query", issue_title)
        is_test_related = query_result.get("is_test_related", False)
        
        logger.info(f"Generated search query: {search_query} (Test Related: {is_test_related})")
        
        # Embed the query instead of the raw issue
        query_embedding = self.embedder.embed_function(search_query, None, "", 512)
        
        # 2. Retrieve Candidates (Mixed Pool)
        # Fetch slightly more if we plan to filter
        k_fetch = k + 10 if not is_test_related else k
        retrieval_results = self.retriever.retrieve(query_embedding, k=k_fetch)
        
        if not retrieval_results:
            logger.warning("No candidates retrieved.")
            return [], [], {}

        # 2.5 Filter Test Files if irrelevant
        if not is_test_related:
            filtered_results = []
            for res in retrieval_results:
                # Check for "test" keyword in file path or file name
                # Heuristic: file starts with test_ or ends with _test.py, or path contains /tests/ or /test/
                fpath = res.file_path.lower()
                fname = res.name.lower()
                
                is_test_file = (
                    "/test/" in fpath or "/tests/" in fpath or 
                    "test_" in fpath.split("/")[-1] or 
                    "_test.py" in fpath or
                    fname.startswith("test_")
                )
                
                if not is_test_file:
                    filtered_results.append(res)
                else:
                    logger.debug(f"Filtering out test candidate: {res.file_path} :: {res.name}")
            
            # If we filtered everything, fall back to original to avoid empty set
            if filtered_results:
                retrieval_results = filtered_results[:k]
            else:
                logger.warning("All candidates were tests but filtered. Reverting filter.")
                retrieval_results = retrieval_results[:k]

        # 3. Initial Enrichment (Code & Graph)
        initial_candidates = self._enrich_candidates(retrieval_results)
        
        # 4. Separation & Consistency Enforcement
        #    - Separate into Files, Classes, Functions
        #    - Ensure parents are present for lower-level entities
        
        candidates_files = []
        candidates_classes = []
        candidates_funcs = []
        
        # Index for quick lookup of existing IDs
        existing_ids = {c['id'] for c in initial_candidates}
        
        for cand in initial_candidates:
            etype = cand.get('entity_type', 'function')
            if etype == 'file':
                candidates_files.append(cand)
            elif etype == 'class':
                candidates_classes.append(cand)
            else:
                candidates_funcs.append(cand)
                
        # Fetch contexts for ALL functions and classes to find missing parents
        consistency_ids = [c['id'] for c in candidates_funcs + candidates_classes]
        context_map = self.graph_store.get_node_context(consistency_ids)
        
        # Helper to hydrate a node from Neo4j dict
        def _hydrate_and_add(node_data, target_list, entity_type):
            node_id = node_data.get('id')
            if not node_id or node_id in existing_ids:
                return

            # Create candidate dict
            new_cand = {
                'id': node_id,
                'entity_type': entity_type,
                'name': node_data.get('name', '') if entity_type != 'file' else node_data.get('path', ''),
                'file_path': node_data.get('path') if entity_type == 'file' else None, # will be fixed below
                'class_name': None,
                'score': 0.0, # Not retrieved directly
                'signature': node_data.get('signature', ''),
                'docstring': None,
                'start_line': node_data.get('start_line', 0),
                'end_line': node_data.get('end_line', 0)
            }
            
            # For non-files, we need the file path to read code
            # The node_data might not have it directly if it came from a relationship
            # But wait, get_node_context returns {parent_class: Node, parent_file: Node}
            # The node_data passed here is the PARENT itself.
            
            if entity_type == 'file':
                new_cand['file_path'] = node_data.get('path')
            elif entity_type == 'class':
                 # Use the file_id effectively? No, we need path.
                 # Optimization: The parent_file node is usually available in the context of the child.
                 # But here 'node_data' IS the parent class. We don't know ITS file path easily unless we query it or it's in properties.
                 # 'Path' is usually not on Class nodes in my schema (only file_id).
                 # We might need to rely on the CHILD's info.
                 pass

            # Getting code content
            # Simplification: If we can't easily get the file path for a Class node from its dict,
            # we might skip code reading or try our best.
            # However, usually Class node has `repo` and `file_id`.
            # Let's assume we can get it or we skip code for now if complex.
            # Actually, let's try to get file path from the CHILD that triggered this.
            
            pass 
            
        # Refined Consistency Logic
        # We process functions -> ensure class -> ensure file
        
        # 1. Functions -> Classes
        for func in candidates_funcs:
            ctx = context_map.get(func['id'], {})
            p_class = ctx.get('parent_class')
            p_file = ctx.get('parent_file')
            
            # Add Class if missing
            if p_class and p_class.get('id') not in existing_ids:
                # We need file path to read code. Use 'p_file' path if available.
                f_path = p_file.get('path') if p_file else func.get('file_path')
                cand = self._create_candidate_from_node(p_class, 'class', f_path)
                if cand:
                    candidates_classes.append(cand)
                    existing_ids.add(cand['id'])
            
            # Add File if missing
            if p_file and p_file.get('id') not in existing_ids:
                cand = self._create_candidate_from_node(p_file, 'file', p_file.get('path'))
                if cand:
                    candidates_files.append(cand)
                    existing_ids.add(cand['id'])

        # 2. Classes -> Files
        for cls in candidates_classes:
            # We might have just added this class, so check context
            # If it was added above, we likely added the file too.
            # If it was in original retrievals, check context.
            if cls['id'] in context_map:
                ctx = context_map[cls['id']]
                p_file = ctx.get('parent_file')
                if p_file and p_file.get('id') not in existing_ids:
                    cand = self._create_candidate_from_node(p_file, 'file', p_file.get('path'))
                    if cand:
                        candidates_files.append(cand)
                        existing_ids.add(cand['id'])

        # Sort lists by score (descending) 
        # (New entities have 0.0, so they go to bottom, which is fine)
        candidates_files.sort(key=lambda x: x['score'], reverse=True)
        candidates_classes.sort(key=lambda x: x['score'], reverse=True)
        candidates_funcs.sort(key=lambda x: x['score'], reverse=True)

        grouped_candidates = {
            'files': candidates_files[:Config.LLM_INPUT_LIMIT], 
            'classes': candidates_classes[:Config.LLM_INPUT_LIMIT],
            'functions': candidates_funcs[:Config.LLM_INPUT_LIMIT]
        }
        
        # 4. LLM Selection (Re-ranking)
        logger.info(f"Selecting from grouped candidates: {len(candidates_files)}F, {len(candidates_classes)}C, {len(candidates_funcs)}M")
        
        try:
            selected_items, token_usage = self.llm_service.select_functions(issue_title, issue_body, grouped_candidates)
        except Exception as e:
            logger.error(f"LLM selection failed: {e}")
            # Fallback: Flatten and return top mixed
            flat = candidates_funcs + candidates_classes + candidates_files
            flat.sort(key=lambda x: x['score'], reverse=True)
            return flat[:Config.LLM_SELECTION_COUNT], flat, {}

        # Construct Final Ranked List
        # selected_items is a list of dicts with 'entity_type' and 'id'
        final_ranked_list = []
        selected_ids = set()
        
        # Flatten grouped candidates for lookup
        all_candidates_map = {c['id']: c for c in candidates_files + candidates_classes + candidates_funcs}
        
        for item in selected_items:
            # item has the reasoning and new type, find original
            orig = all_candidates_map.get(item['id'])
            if orig:
                # Merge LLM info
                merged = orig.copy()
                merged['llm_reasoning'] = item.get('reasoning')
                merged['entity_type'] = item.get('entity_type', orig['entity_type']) # Trust LLM type?
                final_ranked_list.append(merged)
                selected_ids.add(item['id'])
                
        # Fill remaining with top functions (or classes/files?)
        # Fallback to function scores
        for cand in candidates_funcs:
            if cand['id'] not in selected_ids:
                final_ranked_list.append(cand)
                
        return final_ranked_list, initial_candidates, token_usage

    def _create_candidate_from_node(self, node_data, entity_type, file_path):
        """Helper to create a candidate dict from a Neo4j node dict."""
        try:
            cand = {
                'id': node_data.get('id'),
                'entity_type': entity_type,
                'name': node_data.get('name', '') if entity_type != 'file' else node_data.get('path', ''),
                'file_path': file_path,
                'class_name': None, # We don't easily know the class name for a generic node unless passed
                'score': 0.0,
                'signature': node_data.get('signature', ''),
                'docstring': None,
                'start_line': node_data.get('start_line', 0),
                'end_line': node_data.get('end_line', 0)
            }
            
            # Read Code
            code_content = ""
            if file_path:
                full_path = os.path.join(self.repo_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        if entity_type == 'file':
                            code_content = f.read()
                        else:
                            lines = f.readlines()
                            start = max(0, cand['start_line'] - 1)
                            end = min(len(lines), cand['end_line'])
                            code_content = "".join(lines[start:end])
            
            if not code_content:
                code_content = cand['signature'] or "Code not available"
                
            cand['code'] = code_content
            return cand
        except Exception as e:
            logger.warning(f"Error hydrating candidate {node_data.get('id')}: {e}")
            return None

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
