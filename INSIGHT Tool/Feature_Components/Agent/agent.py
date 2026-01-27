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
    
    # Patch generation (optional)
    generate_patch: bool  # Flag to enable/disable patch generation
    patch: str            # Generated patch output (includes CoT reasoning)
    patch_reasoning: Dict[str, Any]  # Structured CoT reasoning steps
    
    # Token tracking
    token_usage: Dict[str, int]
    start_time: float

# --- Agent Class ---
class BugLocalizationAgent:
    """
    Agentic RAG for Bug Localization using LangGraph.
    Orchestrates Planner -> Retriever -> Expander -> Generator -> (optional) Patch Generator.
    
    Patch Generation Methodology:
        Based on "ThinkRepair: Self-Directed Automated Program Repair" (Yin et al., ISSTA 2024)
        and "Structured Chain-of-Thought Prompting for Code Generation" (Li et al., TOSEM 2025).
        Uses a 5-step Chain-of-Thought reasoning process:
        1. Define Repair Objective and Constraints
        2. Evaluate Repair Strategies
        3. Design Minimal Patch
        4. Verify Correctness
        5. Assess Quality and Impact
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
        workflow.add_node("patch_generator", self.patch_generator_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Edges
        workflow.add_edge("planner", "retriever")
        workflow.add_edge("retriever", "expander")
        workflow.add_edge("expander", "selector")
        
        # Conditional edge: selector -> patch_generator OR END
        def should_generate_patch(state: AgentState) -> str:
            if state.get("generate_patch", False):
                return "patch_generator"
            return END
        
        workflow.add_conditional_edges("selector", should_generate_patch, {
            "patch_generator": "patch_generator",
            END: END
        })
        workflow.add_edge("patch_generator", END)
        
        return workflow.compile()


    # --- Nodes ---
    
    def planner_node(self, state: AgentState) -> Dict:
        """Analyze issue and plan search queries (Structured)"""
        logger.info("--- Planner Node ---")
        issue_text = f"Title: {state['issue_title']}\nDescription: {state['issue_body']}"
        
        system_msg = """You are a senior developer debugging a codebase. 
        Analyze the issue report and generate a structured search plan.
        
        Return a JSON object with:
        {
            "semantic_queries": ["natural language description of functionality"],
            "lexical_queries": ["precise error messages", "function names", "constants"],
            "must_include_tokens": ["token1", "token2"] (Optional: tokens that MUST be present in valid results)
        }
        """
        
        prompt = f"Issue:\n{issue_text}\n\nProvide the search plan in JSON."
        
        response = self.llm_service.get_response(prompt, system_message=system_msg, json_mode=True)
        
        # Parse JSON
        plan = {"semantic_queries": [], "lexical_queries": [], "must_include_tokens": []}
        try:
            start_idx = response.find('{')
            if start_idx != -1:
                plan = json.JSONDecoder().raw_decode(response[start_idx:])[0]
        except Exception as e:
            logger.error(f"Failed to parse Planner JSON: {e}")
            # Fallback
            return {"current_plan": response, "messages": [AIMessage(content="Plan parse failed, check logs.")]}

        # Update token usage
        self._update_tokens(state, len(prompt.split()), len(response.split()))
        
        # Store structured plan in state (as string or dict? State definition has string 'current_plan')
        # We'll serialize it or add a new state key if we could, but let's just serialize to string for compatibility 
        # or rely on the next node parsing it? 
        # Better: Update AgentState definition to hold 'structured_plan'. 
        # Since I can't easily change the TypedDict definition in one go without replacing the whole file,
        # I will store it in 'current_plan' as a JSON string.
        
        return {
            "current_plan": json.dumps(plan),
            "messages": [AIMessage(content=f"Plan generated: {len(plan.get('semantic_queries',[]))} semantic, {len(plan.get('lexical_queries',[]))} lexical.")]
        }

    def retriever_node(self, state: AgentState) -> Dict:
        """Execute Hybrid Search (Dense + Sparse + RRF)"""
        logger.info("--- Retriever Node (Hybrid) ---")
        
        if not self.embedder or not self.vector_tool:
             logger.warning("Embedder/VectorStore unavailable. Skipping retrieval.")
             return {"candidate_functions": [], "messages": [AIMessage(content="Search unavailable.")]}

        # Parse plan
        try:
            plan = json.loads(state['current_plan'])
        except:
            # Fallback for legacy string plans
            plan = {"semantic_queries": state['current_plan'].split('\n'), "lexical_queries": [], "must_include_tokens": []}

        semantic_queries = plan.get('semantic_queries', [])
        lexical_queries = plan.get('lexical_queries', [])
        must_include = [t.lower() for t in plan.get('must_include_tokens', [])]
        
        candidates = {} # Map id -> {meta, score}
        
        # 1. Process Semantic Queries (Hybrid: Dense + BM25)
        for q in semantic_queries:
            if not q: continue
            try:
                # Embed for Dense
                embeddings = self.embedder.embed_batch([q])
                if len(embeddings) == 0: continue
                q_emb = embeddings[0]
                
                # Hybrid Search
                indices, scores, metadata = self.vector_store.search_hybrid(q_emb, q, k=15)
                
                for meta, score in zip(metadata, scores):
                    mid = meta.get('id')
                    if mid:
                        if mid not in candidates:
                            candidates[mid] = {'meta': meta, 'score': score}
                        else:
                            # Keep max score
                            if score > candidates[mid]['score']:
                                candidates[mid]['score'] = score
            except Exception as e:
                logger.error(f"Semantic search failed for '{q}': {e}")

        # 2. Process Lexical Queries
        for q in lexical_queries:
             if not q: continue
             try:
                embeddings = self.embedder.embed_batch([q])
                if len(embeddings) == 0: continue
                q_emb = embeddings[0]
                
                indices, scores, metadata = self.vector_store.search_hybrid(q_emb, q, k=15)
                
                for meta, score in zip(metadata, scores):
                    mid = meta.get('id')
                    if mid:
                        if mid not in candidates:
                            candidates[mid] = {'meta': meta, 'score': score}
                        else:
                            if score > candidates[mid]['score']:
                                candidates[mid]['score'] = score
             except Exception as e:
                logger.error(f"Lexical search failed for '{q}': {e}")
                
        
        # Sort by score (Initial Ranking)
        sorted_candidates = sorted(candidates.values(), key=lambda x: x['score'], reverse=True)
        final_list = []
        for item in sorted_candidates:
            c = item['meta'].copy()
            c['score'] = item['score']
            final_list.append(c)
            
        logger.info(f"Candidates before filtering: {len(final_list)}")
        
        # 3. Filter by Must-Include Tokens (Post-processing)
        filtered_candidates = []
        if must_include:
            logger.info(f"Filtering results by tokens: {must_include}")
            
            def check_tokens(c, mode='all'):
                meta_text = f"{c.get('name','')} {c.get('file_path','')} {c.get('signature','')} {c.get('docstring','')}".lower()
                tokens_found = [t for t in must_include if t in meta_text]
                if mode == 'all' and len(tokens_found) == len(must_include): return True
                if mode == 'any' and len(tokens_found) > 0: return True
                try:
                    code = self._get_source_code(c).lower()
                    if code:
                         tokens_found_src = [t for t in must_include if t in code]
                         if mode == 'all' and len(tokens_found_src) == len(must_include): return True
                         if mode == 'any' and len(tokens_found_src) > 0: return True
                except Exception:
                    pass
                return False

            filtered_candidates = [c for c in final_list if check_tokens(c, 'all')]
            
            if not filtered_candidates:
                logger.warning("Strict filter returned 0 results. Retrying with ANY token match...")
                filtered_candidates = [c for c in final_list if check_tokens(c, 'any')]
                
            if not filtered_candidates:
                 logger.warning("All filters failed. Returning top unfiltered candidates.")
                 filtered_candidates = final_list
        else:
            filtered_candidates = final_list

        logger.info(f"Retrieved {len(filtered_candidates)} candidates after token filtering")
        
        # 4. LLM Reranking (Take Top 50 -> Rank -> Top 15)
        # Only rerank if we have enough candidates to justify it
        if len(filtered_candidates) > 5:
            rerank_pool = filtered_candidates[:50] # Rerank top 50
            logger.info(f"Reranking top {len(rerank_pool)} candidates with LLM...")
            try:
                final_ranked = self._rerank_candidates(state['issue_title'], state['issue_body'], rerank_pool)
                # Take top 15 from reranked
                final_candidates = final_ranked[:15]
                logger.info("LLM Reranking complete.")
            except Exception as e:
                logger.error(f"Reranking failed: {e}. Falling back to original order.")
                final_candidates = filtered_candidates[:15]
        else:
            final_candidates = filtered_candidates

        logger.info(f"Final retrieved count: {len(final_candidates)}")

        return {
            "candidate_functions": final_candidates,
            "messages": [AIMessage(content=f"Retrieved {len(final_candidates)} candidates.")]
        }

    def _rerank_candidates(self, issue_title: str, issue_body: str, candidates: List[Dict]) -> List[Dict]:
        """Use LLM to rerank candidates by relevance to the issue."""
        if not candidates: return []
        
        # Prepare list for prompt
        cand_text = ""
        for i, c in enumerate(candidates):
            # Include minimal info to save tokens: Name, File, Docstring (truncated)
            doc = (c.get('docstring') or "").split('\n')[0][:100]
            cand_text += f"[{i}] {c.get('name')} ({c.get('file_path')})\n    Doc: {doc}\n"
        
        system_msg = """You are a Code Retrieval Reranker.
        Rank the candidates based on their relevance to the Issue.
        Prioritize functions that implement the logic described or are likely locations of the bug.
        Ignore irrelevant files (e.g. tests, cli, documentation) unless the issue specifically targets them.
        Return ONLY a JSON list of indices in order of relevance, e.g. [5, 0, 12, ...].
        """
        
        prompt = f"Issue: {issue_title}\n{issue_body[:500]}\n\nCandidates:\n{cand_text}\n\nRank indices:"
        
        response = self.llm_service.get_response(prompt, system_message=system_msg, json_mode=True)
        
        try:
             # Extract list
             import ast
             # Try simple parsing first in case not pure JSON
             start = response.find('[')
             end = response.rfind(']') + 1
             if start != -1 and end != -1:
                 indices = json.loads(response[start:end])
             else:
                 indices = []
             
             ranked_candidates = []
             seen_idx = set()
             
             # Add valid indices
             for idx in indices:
                 if isinstance(idx, int) and 0 <= idx < len(candidates):
                     ranked_candidates.append(candidates[idx])
                     seen_idx.add(idx)
             
             # Add remaining candidates at the end
             for i, c in enumerate(candidates):
                 if i not in seen_idx:
                     ranked_candidates.append(c)
                     
             return ranked_candidates
        except Exception as e:
            logger.error(f"Failed to parse rerank response: {e}")
            return candidates

    def expander_node(self, state: AgentState) -> Dict:
        """Expand search using Knowledge Graph (Hydrated)"""
        logger.info("--- Expander Node ---")
        candidates = state['candidate_functions']
        
        if not self.graph_store:
            return {"candidate_functions": candidates, "messages": [AIMessage(content="Graph expansion skipped.")]}
            
        expanded_candidates = list(candidates) # Start with retrieved
        seen_ids = set(c['id'] for c in candidates if c.get('id'))
        
        # Expand top k candidates
        k_expand = 5
        for seed in candidates[:k_expand]:
            seed_id = seed.get('id')
            if not seed_id: continue
            
            # 1. Calls/Called (Neighbors)
            neighbors = self.graph_store.get_function_neighbors(seed_id)
            
            # 2. Siblings (Same Class/File) - Critical for "Close Shot" misses
            siblings = self.graph_store.get_siblings(seed_id)
            
            # Combine
            all_related = neighbors + siblings
            
            for n in all_related:
                nid = n.get('id')
                if nid and nid not in seen_ids:
                    # Hydrate metadata from VectorStore
                    full_meta = self.vector_store.get_metadata_by_id(nid)
                    if full_meta:
                        full_meta['entity_type'] = n.get('type', 'function') # Preserve type if useful
                        # Tag source for debugging
                        # full_meta['expansion_source'] = 'graph' 
                        expanded_candidates.append(full_meta)
                        seen_ids.add(nid)
                    else:
                        # If not in vector store, use what we have from graph
                        n['entity_type'] = 'function' 
                        expanded_candidates.append(n)
                        seen_ids.add(nid)
        
        logger.info(f"Expanded to {len(expanded_candidates)} total candidates")
         
        return {
            "candidate_functions": expanded_candidates,
            "messages": [AIMessage(content=f"Expanded candidates to {len(expanded_candidates)} using graph.")]
        }

    def selector_node(self, state: AgentState) -> Dict:
        """Selector Node: Identify bugs with Evidence (Claim-Evidence Mapping)"""
        logger.info("--- Selector Node ---")
        candidates = state['candidate_functions']
        issue_text = f"Title: {state['issue_title']}\nDescription: {state['issue_body']}"
        
        # Format candidates for LLM
        valid_candidates = [c for c in candidates if c.get('entity_type') == 'function']
        
        # Limit to fit context window
        limit = 30 
        sliced_candidates = valid_candidates[:limit]
        
        # Log candidates sent to LLM for debugging
        logger.info(f"--- Selector Candidates ({len(sliced_candidates)}) ---")
        for i, c in enumerate(sliced_candidates):
             logger.info(f"#{i+1}: {c.get('name')} | {c.get('file_path')} | Score: {c.get('score', 0):.4f}")

        candidate_str = ""
        for i, c in enumerate(sliced_candidates):
            candidate_str += f"Candidate {i+1} (ID: {c.get('id')}):\n"
            candidate_str += f"Name: {c.get('name')}\n"
            candidate_str += f"File: {c.get('file_path') or c.get('path')}\n"
            candidate_str += f"Signature: {c.get('signature')}\n"
            
            # Include body snippet
            code_snippet = self._get_source_code(c)
            if code_snippet:
                candidate_str += f"Code:\n{code_snippet}\n"
            else:
                 logger.warning(f"No source code found for candidate #{i+1}: {c.get('name')}")
                 candidate_str += "Code: [Not Available]\n"
            
            if c.get('docstring'):
                candidate_str += f"Docstring: {c.get('docstring')}\n"
            candidate_str += "\n"
            
        system_msg = """You are a Lead Investigator validating a bug report.
        Your task is to identify the top 3-5 most suspicious bug locations and provide hard EVIDENCE.
        
        The code snippets provided are prefixed with [file_path:line_number].
        For each candidate, check if it contains the bug described.
        
        Return a JSON object with the following schema:
        {
            "analysis_summary": "High-level summary of the bug...",
            "bug_locations": [
                {
                    "candidate_index": 1, 
                    "confidence": "HIGH" | "MEDIUM" | "LOW",
                    "reasoning": "Concise, single-sentence explanation of why this is the bug...",
                    "evidence": [
                        {"file": "path/to/file.py", "lines": [10, 11, 12]}
                    ]
                }
            ]
        }
        
        Rules:
        1. Identify at least 3 suspicious locations if possible, even if confidence is MEDIUM or LOW.
        2. Rank your findings by likelyhood/confidence.
        3. 'evidence' must cite specific lines from the provided snippets.
        4. Do NOT guess blindly, but be expansive in your selection to ensure the bug is caught.
        5. Do NOT select the same function code location multiple times.
        6. The 'reasoning' must be strictly about THIS candidate's relevance to the bug. Do not mention other candidates.
        """
        
        prompt = f"Issue:\n{issue_text}\n\nCandidates:\n{candidate_str}\n\nGenerate Bug Report JSON."
        
        response = self.llm_service.get_response(prompt, system_message=system_msg, json_mode=True)
        
        selected = []
        seen_functions = set() # Track (file_path, function_name) to prevent duplicates

        try:
            # Parse JSON
            start_idx = response.find('{')
            if start_idx == -1: raise json.JSONDecodeError("No JSON found", response, 0)
            
            data, _ = json.JSONDecoder().raw_decode(response[start_idx:])
            
            locations = data.get('bug_locations', [])
            summary = data.get('analysis_summary', '')
            
            for loc in locations:
                idx = loc.get('candidate_index')
                if isinstance(idx, int):
                    actual_idx = idx - 1
                    if 0 <= actual_idx < len(sliced_candidates):
                        cand = sliced_candidates[actual_idx]
                        
                        # Deduplication check
                        fpath = cand.get('file_path') or cand.get('path')
                        fname = cand.get('name')
                        unique_key = (fpath, fname)
                        
                        if unique_key in seen_functions:
                            continue
                        seen_functions.add(unique_key)

                        # Enrich candidate with RAG output
                        cand['analysis'] = loc.get('reasoning', '')
                        cand['confidence'] = loc.get('confidence', '')
                        cand['evidence'] = loc.get('evidence', [])
                        
                        # Append the overall summary too if needed
                        cand['report_summary'] = summary
                        
                        selected.append(cand)

        except Exception as e:
            logger.error(f"Failed to parse GroundedGen JSON: {e}")
            logger.error(f"Raw response: {response}")
        
        # Update token usage
        self._update_tokens(state, len(prompt.split()), len(response.split()))
        
        return {
            "selected_functions": selected,
            "messages": [AIMessage(content=f"Identified {len(selected)} locations with evidence.")]
        }

    def _get_source_code(self, candidate: Dict[str, Any]) -> str:
        """
        Retrieve source code for a candidate with line numbers for grounding.
        Format: [file_path:line_number] code_content
        """
        fpath = candidate.get('file_path') or candidate.get('path')
        if not fpath: return ""
        
        # Resolve absolute path
        # If fpath is absolute, use it. Else join with repo_dir.
        import os
        if os.path.isabs(fpath):
            abs_path = fpath
        else:
            # repo_dir might be set in __init__
            if not self.repo_dir: return ""
            abs_path = os.path.join(self.repo_dir, fpath)
            
        if not os.path.exists(abs_path):
            return ""
            
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            start = candidate.get('start_line', 1)
            end = candidate.get('end_line', len(lines))
            
            # 1-based indexing correction
            start_idx = max(0, start - 1)
            end_idx = min(len(lines), end)
            
            snippet = []
            for i in range(start_idx, end_idx):
                line_num = i + 1
                line_content = lines[i].rstrip()
                # Format: [path:line] content
                # Use relative path for brevity in prompt
                snippet.append(f"[{fpath}:{line_num}] {line_content}")
                
            return "\n".join(snippet)
        except Exception as e:
            logger.error(f"Error reading source {abs_path}: {e}")
            return ""

    def _update_tokens(self, state: AgentState, input_tokens: int, output_tokens: int):
        if 'token_usage' not in state:
             state['token_usage'] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        state['token_usage']['input_tokens'] += input_tokens
        state['token_usage']['output_tokens'] += output_tokens
        state['token_usage']['total_tokens'] += input_tokens + output_tokens

    def patch_generator_node(self, state: AgentState) -> Dict:
        """
        Chain-of-Thought Patch Generator Node.
        
        Generates patches for ALL selected bug locations (multiple files supported).
        
        Implements structured reasoning for patch generation based on:
        - ThinkRepair (Yin et al., ISSTA 2024) - Self-directed CoT reasoning
        - SCoT (Li et al., TOSEM 2025) - Structured intermediate reasoning
        """
        logger.info("--- Patch Generator Node (Chain-of-Thought) ---")
        
        selected_functions = state.get('selected_functions', [])
        if not selected_functions:
            logger.warning("No selected functions for patch generation")
            return {
                "patch": "",
                "patch_reasoning": {},
                "messages": [AIMessage(content="No bug locations identified for patch generation.")]
            }
        
        issue_text = f"Title: {state['issue_title']}\nDescription: {state['issue_body']}"
        
        # Build context for ALL selected functions
        bug_locations_text = ""
        for i, func in enumerate(selected_functions):
            file_path = func.get('file_path') or func.get('path', '')
            code = self._get_source_code(func)
            analysis = func.get('analysis', '')
            
            bug_locations_text += f"""
--- Bug Location {i+1} ---
File: {file_path}
Function: {func.get('name', 'Unknown')}
Analysis: {analysis}
Code:
```
{code}
```
"""
        
        # Build the Chain-of-Thought prompt for multiple files
        system_msg = """You are an expert software engineer specializing in Automated Program Repair.
Your task is to generate patches for ALL identified bug locations using a structured Chain-of-Thought (CoT) process.

You MUST output a JSON object with the following structure:

{
  "step1_objective": {
    "think": "What must be fixed and what constraints apply?",
    "objective": "Description of what needs to be fixed",
    "constraints": ["list of constraints"]
  },
  "step2_strategy": {
    "think": "What are the possible repair approaches?",
    "selected": "Chosen strategy",
    "rationale": "Why this strategy best fits"
  },
  "step3_verification": {
    "think": "Does this fix all cases?",
    "bug_case": "How it fixes the reported bug",
    "edge_cases": "How edge cases are handled"
  },
  "patches": [
    {
      "file": "path/to/file1.py",
      "function_name": "function_name",
      "start_line": 45,
      "end_line": 52,
      "corrected_code": "The corrected code snippet",
      "commit_message": "Concise commit message for this fix"
    },
    {
      "file": "path/to/file2.py",
      "function_name": "another_function",
      "start_line": 10,
      "end_line": 15,
      "corrected_code": "The corrected code snippet",
      "commit_message": "Concise commit message for this fix"
    }
  ],
  "overall_commit_message": "Single commit message summarizing all fixes"
}

IMPORTANT: 
- Output ONLY valid JSON. No markdown formatting outside the JSON.
- Generate a patch for EACH bug location provided.
- The corrected_code should be the COMPLETE fixed code for the specified line range.
"""
        
        prompt = f"""Issue:
{issue_text}

Identified Bug Locations:
{bug_locations_text}

Generate the Chain-of-Thought patch repair JSON with patches for ALL bug locations."""

        response = self.llm_service.get_response(prompt, system_message=system_msg, json_mode=True)
        
        # Parse the CoT response
        patch_reasoning = {}
        formatted_patch = ""
        
        try:
            # Extract JSON
            start_idx = response.find('{')
            if start_idx == -1:
                raise json.JSONDecodeError("No JSON found", response, 0)
            
            data, _ = json.JSONDecoder().raw_decode(response[start_idx:])
            patch_reasoning = data
            
            # Format the output for multiple patches
            formatted_patch = self._format_patches(data)
            
            logger.info(f"Patch generation complete: {len(data.get('patches', []))} patches generated")
            
        except Exception as e:
            logger.error(f"Failed to parse patch generator response: {e}")
            logger.error(f"Raw response: {response}")
            formatted_patch = f"# Error generating patch: {e}\n# Raw response:\n{response}"
        
        # Update token usage
        self._update_tokens(state, len(prompt.split()), len(response.split()))
        
        return {
            "patch": formatted_patch,
            "patch_reasoning": patch_reasoning,
            "messages": [AIMessage(content=f"Generated {len(data.get('patches', []))} patches with Chain-of-Thought reasoning.")]
        }

    def _format_patches(self, data: Dict[str, Any]) -> str:
        """
        Format multiple patches for GitHub comment.
        
        Returns the patches as code snippets with line numbers.
        Full CoT reasoning is preserved in patch_reasoning for debugging.
        """
        lines = []
        
        patches = data.get('patches', [])
        overall_commit = data.get('overall_commit_message', '')
        
        if not patches:
            return "*No patches generated*"
        
        if overall_commit:
            lines.append(f"**Summary:** {overall_commit}")
            lines.append("")
        
        for i, patch in enumerate(patches):
            if i > 0:
                lines.append("---")  # Separator between patches
                lines.append("")
            
            file_path = patch.get('file', 'Unknown')
            func_name = patch.get('function_name', '')
            start_line = patch.get('start_line')
            end_line = patch.get('end_line')
            corrected_code = patch.get('corrected_code', '')
            commit_msg = patch.get('commit_message', '')
            
            lines.append(f"**File:** `{file_path}`")
            if func_name:
                lines.append(f"**Function:** `{func_name}`")
            if start_line and end_line:
                lines.append(f"**Lines:** {start_line}-{end_line}")
            if commit_msg:
                lines.append(f"**Fix:** {commit_msg}")
            lines.append("")
            
            if corrected_code:
                lines.append("**Suggested Fix:**")
                lines.append("```python")
                # Add line numbers to each line of the corrected code
                code_lines = corrected_code.split('\n')
                line_num = start_line if start_line else 1
                for code_line in code_lines:
                    lines.append(f"{line_num}: {code_line}")
                    line_num += 1
                lines.append("```")
            else:
                lines.append("*No fix generated for this location*")
            
            lines.append("")
        
        return "\n".join(lines)

    def localize(self, issue_title: str, issue_body: str, generate_patch: bool = False) -> tuple[List[Dict], List[Dict], Dict, str, Dict]:
        """
        Main entry point for localization.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body/description
            generate_patch: If True, run the chain-of-thought patch generator after localization
            
        Returns: 
            (selected_funcs, all_candidates, token_usage, patch, patch_reasoning)
            - patch and patch_reasoning will be empty if generate_patch is False
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
            "generate_patch": generate_patch,
            "patch": "",
            "patch_reasoning": {},
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            "start_time": start_time
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        return (
            final_state.get('selected_functions', []),
            final_state.get('candidate_functions', []),
            final_state.get('token_usage', {}),
            final_state.get('patch', ''),
            final_state.get('patch_reasoning', {})
        )

