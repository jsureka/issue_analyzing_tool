import logging
import json
import operator
import time
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# Internal imports
from ..KnowledgeBase.llm_service import LLMService
from ..KnowledgeBase.vector_store import VectorStore
from ..KnowledgeBase.graph_store import GraphStore
from ..KnowledgeBase.embedder import CodeEmbedder
from .tools import VectorSearchTool, GraphNeighborsTool, GraphContextTool

logger = logging.getLogger(__name__)

# --- State Definition ---
class AgentState(TypedDict):
    issue_title: str
    issue_body: str
    repo_name: str
    
    # Message history for the agent
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # structured state
    current_plan: str
    candidate_functions: List[Dict] # Accumulated candidates
    selected_functions: List[Dict]  # Final selection
    
    # Token tracking
    token_usage: Dict[str, int]
    start_time: float

# --- Agent Class ---
class BugLocalizationAgent:
    """
    Agentic RAG for Bug Localization using LangGraph.
    Orchestrates Planner -> Retriever -> Expander -> Selector.
    """
    
    def __init__(self, repo_name: str, repo_dir: str):
        self.repo_name = repo_name
        self.repo_dir = repo_dir
        
        from config import Config
        self.config = Config
        
        self.llm_service = LLMService()
        self.graph_store = GraphStore(Config.NEO4J_URI, Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        self.vector_store = VectorStore()
        
        self.index_base_dir = Config.KNOWLEDGE_BASE_DIR

        self.embedder = None
        self._load_resources()
        
        if self.embedder:
            self.vector_tool = VectorSearchTool(self.vector_store, self.embedder, self.repo_name)
        else:
            logger.warning("Embedder not initialized, VectorSearchTool will be disabled.")
            self.vector_tool = None
            
        self.graph_neighbor_tool = GraphNeighborsTool(self.graph_store, self.repo_name)
        self.graph_context_tool = GraphContextTool(self.graph_store, self.repo_name)
        
        self.workflow = self._build_workflow()
        
    def _load_resources(self):
        """Load vector store and embedder"""
        try:
            from pathlib import Path
            safe_repo_name = self.repo_name.replace('/', '_')
            repo_base = Path(self.index_base_dir) / safe_repo_name
            
            if not repo_base.exists():
                logger.error(f"No index directory found for {self.repo_name} at {repo_base}")
                return

            files = list(repo_base.glob("**/index.faiss"))
            if not files:
                 logger.error(f"No index.faiss found in {repo_base}")
                 return
                 
            # Use most recent index
            latest_index = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
            metadata_path = latest_index.parent / "metadata.json"
            
            self.embedder = CodeEmbedder()
            self.embedder.load_model()
            
            self.vector_store.create_index()
            self.vector_store.load_index(str(latest_index))
            self.vector_store.load_metadata(str(metadata_path))
            
            logger.info(f"BugLocalizationAgent loaded index from {latest_index}")
            
        except Exception as e:
            logger.error(f"Failed to load resources: {e}")

    def _get_source_code(self, candidate: Dict) -> str:
        """Fetch source code for a candidate from disk"""
        try:
            file_path = candidate.get('file_path') or candidate.get('path')
            if not file_path:
                return ""
                
            # Handle potential path issues. file_path should be relative
            import os
            full_path = os.path.join(self.repo_dir, file_path)
            
            if not os.path.exists(full_path):
                # Try finding it if path is weird?
                return ""
                
            start_line = candidate.get('start_line')
            end_line = candidate.get('end_line')
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            if start_line and end_line:
                # 1-based indexing
                s = max(0, start_line - 1)
                e = min(len(lines), end_line)
                return "".join(lines[s:e])
            else:
                # Fallback to first 50 lines if no range?
                return "".join(lines[:50])
                
        except Exception as e:
            logger.warning(f"Failed to read source for {candidate.get('name')}: {e}")
            return ""

    def _build_workflow(self) -> Any:
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("retriever", self.retriever_node)
        workflow.add_node("expander", self.expander_node)
        workflow.add_node("selector", self.selector_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Edges
        workflow.add_edge("planner", "retriever")
        workflow.add_edge("retriever", "expander")
        workflow.add_edge("expander", "selector")
        workflow.add_edge("selector", END)
        
        return workflow.compile()

    # --- Nodes ---
    
    def planner_node(self, state: AgentState) -> Dict:
        """Analyze issue and plan search queries"""
        logger.info("--- Planner Node ---")
        issue_text = f"Title: {state['issue_title']}\nDescription: {state['issue_body']}"
        
        system_msg = """You are a senior developer debugging a codebase. 
        Analyze the issue report and generate specific search queries to find the code responsible for the bug.
        Focus on identifying unique keywords, method names, or class names mentioned in the issue.
        Return 3 distinct search queries."""
        
        prompt = f"Issue:\n{issue_text}\n\nProvide 3 search queries separated by newlines."
        
        response = self.llm_service.get_response(prompt, system_message=system_msg)
        
        # Update token usage
        self._update_tokens(state, len(prompt.split()), len(response.split()))
        
        return {
            "current_plan": response,
            "messages": [AIMessage(content=f"Plan:\n{response}")]
        }

    def retriever_node(self, state: AgentState) -> Dict:
        """Execute vector search based on plan"""
        logger.info("--- Retriever Node ---")
        
        if not self.embedder or not self.vector_tool:
             logger.warning("Embedder/VectorTool not available. Skipping retrieval.")
             return {"candidate_functions": [], "messages": [AIMessage(content="Vector search unavailable.")]}

        queries = state['current_plan'].split('\n')
        queries = [q.strip() for q in queries if q.strip()]
        
        candidates = []
        seen_ids = set()
        
        for q in queries[:3]: # Limit to 3 queries
            # Use tool logic directly or call tool
            # self.vector_tool._run(q) return string, we want objects.
            # Direct usage of store is cleaner since we are inside the agent logic
            
            try:
                embeddings = self.embedder.embed_batch([q])
                if len(embeddings) == 0:
                     continue
                q_emb = embeddings[0]
                indices, scores, metadata = self.vector_store.search(q_emb, k=10)
                
                for meta in metadata:
                    if meta.get('id') and meta['id'] not in seen_ids:
                        candidates.append(meta)
                        seen_ids.add(meta['id'])
            except Exception as e:
                logger.error(f"Search failed for query '{q}': {e}")
                
        logger.info(f"Retrieved {len(candidates)} unique candidates")
        return {
            "candidate_functions": candidates,
            "messages": [AIMessage(content=f"Retrieved {len(candidates)} candidates.")]
        }

    def expander_node(self, state: AgentState) -> Dict:
        """Expand context using graph (callers/callees)"""
        logger.info("--- Expander Node ---")
        candidates = state['candidate_functions']
        
        # For the top 5 candidates, get neighbors
        top_candidates = candidates[:5]
        expanded_candidates = list(candidates) # Copy
        seen_ids = set(c['id'] for c in candidates)
        
        if not self.graph_store.connect():
             logger.warning("Graph connection failed, skipping expansion")
             return {"candidate_functions": candidates}

        for cand in top_candidates:
            if cand.get('entity_type') == 'function':
                # Get neighbors
                neighbors = self.graph_store.get_function_neighbors(cand['id'], "CALLS")
                for n in neighbors:
                    if n['id'] not in seen_ids:
                        # Need to fetch full metadata for neighbor?
                        # Using dummy/partial metadata for now or query vector store by ID?
                        # Ideally GraphStore returns enough info.
                        # Adding basics.
                        n['entity_type'] = 'function' # Neighbors are functions
                        # Add to candidates
                        expanded_candidates.append(n)
                        seen_ids.add(n['id'])
        
        logger.info(f"Expanded to {len(expanded_candidates)} total candidates")
        return {
            "candidate_functions": expanded_candidates,
            "messages": [AIMessage(content=f"Expanded candidates to {len(expanded_candidates)} using graph.")]
        }

    def selector_node(self, state: AgentState) -> Dict:
        """Select the final buggy functions using LLM"""
        logger.info("--- Selector Node ---")
        candidates = state['candidate_functions']
        issue_text = f"Title: {state['issue_title']}\nDescription: {state['issue_body']}"
        
        # Format candidates for LLM
        valid_candidates = [c for c in candidates if c.get('entity_type') == 'function']
        
        # Limit to fit context window
        limit = 30 
        sliced_candidates = valid_candidates[:limit]
        
        candidate_str = ""
        for i, c in enumerate(sliced_candidates):
            candidate_str += f"Candidate {i+1} (ID: {c.get('id')}):\n"
            candidate_str += f"Name: {c.get('name')}\n"
            candidate_str += f"File: {c.get('file_path') or c.get('path')}\n" # normalize keys
            candidate_str += f"Signature: {c.get('signature')}\n"
            # Include body snippet
            code_snippet = self._get_source_code(c)
            if code_snippet:
                candidate_str += f"Code:\n{code_snippet}\n"
            
            if c.get('docstring'):
                candidate_str += f"Docstring: {c.get('docstring')}\n"
            candidate_str += "\n"
            
        system_msg = """You are a senior developer. 
        Given an issue description and a list of candidate functions, select the ones that are most likely responsible for the bug.
        
        Return a JSON object with the following structure:
        {
            "selected_ids": [1, 2, ...],  // List of integer IDs of the suspicious candidates (1-based index)
            "technical_analysis": "Comparison of the issue against the selected code..." // A single short technical analysis summarizing why these files are selected.
        }
        
        Do NOT provide reasoning for every file. Provide one overall analysis.
        If no candidates are relevant, return empty list for selected_ids and explain why in analysis.
        """
        
        prompt = f"Issue:\n{issue_text}\n\nCandidates:\n{candidate_str}\n\nSelect the buggy functions."
        
        response = self.llm_service.get_response(prompt, system_message=system_msg, json_mode=True)
        
        # Parse JSON
        selected = []
        try:
            # Robust JSON extraction
            # Find the first '{'
            start_idx = response.find('{')
            if start_idx == -1:
                 # No JSON object found
                 raise json.JSONDecodeError("No JSON object found", response, 0)
            
            # Use raw_decode to parse just the JSON part and ignore trailing text
            data, _ = json.JSONDecoder().raw_decode(response[start_idx:])
            
            indices = data.get('selected_ids', [])
            analysis = data.get('technical_analysis', '')
            
            if isinstance(indices, list):
                for idx in indices:
                     if isinstance(idx, int):
                         actual_idx = idx - 1
                         if 0 <= actual_idx < len(sliced_candidates):
                             cand = sliced_candidates[actual_idx]
                             # Attach analysis to the candidate (or handled globally)
                             cand['analysis'] = analysis 
                             selected.append(cand)
                     elif isinstance(idx, str) and idx.isdigit():
                         actual_idx = int(idx) - 1
                         if 0 <= actual_idx < len(sliced_candidates):
                             cand = sliced_candidates[actual_idx]
                             cand['analysis'] = analysis
                             selected.append(cand)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Selector JSON response: {e}")
            logger.error(f"Raw response: {response}")
            # Fallback text parsing logic if needed
            pass
        
        # Update token usage
        self._update_tokens(state, len(prompt.split()), len(response.split()))
        
        return {
            "selected_functions": selected,
            "messages": [AIMessage(content=f"Selected {len(selected)} functions.")]
        }

    def _update_tokens(self, state: AgentState, input_tokens: int, output_tokens: int):
        if 'token_usage' not in state:
             state['token_usage'] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        state['token_usage']['input_tokens'] += input_tokens
        state['token_usage']['output_tokens'] += output_tokens
        state['token_usage']['total_tokens'] += input_tokens + output_tokens

    def localize(self, issue_title: str, issue_body: str) -> tuple[List[Dict], List[Dict], Dict]:
        """
        Main entry point for localization.
        Returns: (selected_funcs, all_candidates, token_usage)
        """
        start_time = time.time()
        initial_state: AgentState = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "repo_name": self.repo_name,
            "messages": [],
            "current_plan": "",
            "candidate_functions": [],
            "selected_functions": [],
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            "start_time": start_time
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        return (
            final_state.get('selected_functions', []),
            final_state.get('candidate_functions', []),
            final_state.get('token_usage', {})
        )
