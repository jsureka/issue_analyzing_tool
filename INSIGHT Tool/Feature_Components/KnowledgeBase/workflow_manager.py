"""
Workflow Manager - Orchestrates the bug localization process using LangGraph
"""

import logging
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
import operator

from .llm_service import LLMService
from .retriever import DenseRetriever
from .graph_store import GraphStore
from .issue_processor import IssueProcessor

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    """State for the bug localization workflow"""
    issue_title: str
    issue_body: str
    repo_name: str
    repo_path: str
    
    # Intermediate states
    processed_issue: Dict[str, Any]
    candidate_functions: List[Dict[str, Any]]
    graph_context: str
    directory_context: List[Dict[str, Any]]
    
    # Outputs
    analysis: str
    hypothesis: str
    patch: str
    final_result: Dict[str, Any]

class WorkflowManager:
    """Manages the LangGraph workflow for bug localization"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.retriever = DenseRetriever()
        self.graph_store = GraphStore()
        # IssueProcessor needs an embedder, which is lazy loaded in knowledgeBase.py
        # We'll initialize it when needed or pass it in. 
        # For now, we'll assume the global one is used or we create a fresh one.
        # To avoid circular imports or complex init, we'll rely on the retriever's embedder if possible
        # or just create a new one.
        from .embedder import CodeEmbedder
        self.embedder = CodeEmbedder()
        self.issue_processor = IssueProcessor(self.embedder)
        
        self.workflow = self._build_graph()
        
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)
        
        # Define nodes
        workflow.add_node("process_issue", self.process_issue)
        workflow.add_node("retrieve_context", self.retrieve_context)
        workflow.add_node("analyze_bug", self.analyze_bug)
        workflow.add_node("generate_patch", self.generate_patch)
        
        # Define edges
        workflow.set_entry_point("process_issue")
        workflow.add_edge("process_issue", "retrieve_context")
        workflow.add_edge("retrieve_context", "analyze_bug")
        workflow.add_edge("analyze_bug", "generate_patch")
        workflow.add_edge("generate_patch", END)
        
        return workflow.compile()
        
    def process_issue(self, state: GraphState) -> Dict[str, Any]:
        """Node: Process the issue text"""
        logger.info("Workflow Step: Processing Issue")
        
        # Ensure embedder is loaded
        if not self.embedder.model:
            self.embedder.load_model()
            
        processed = self.issue_processor.process_issue(
            state["issue_title"], 
            state["issue_body"]
        )
        
        return {"processed_issue": processed}

    def retrieve_context(self, state: GraphState) -> Dict[str, Any]:
        """Node: Retrieve vector and graph context"""
        logger.info("Workflow Step: Retrieving Context")
        
        repo_name = state["repo_name"]
        processed_issue = state["processed_issue"]
        
        # 1. Vector Search (FAISS)
        self.retriever.load_index(repo_name)
        results = self.retriever.retrieve(processed_issue.embedding, k=5)
        
        candidate_functions = []
        function_ids = []
        
        for res in results:
            candidate_functions.append({
                "id": res.function_id,
                "name": res.function_name,
                "file_path": res.file_path,
                "snippet": getattr(res, "snippet", ""),
                "score": res.similarity_score,
                "language": getattr(res, "language", "python"),
                "line_range": [res.start_line, res.end_line]
            })
            function_ids.append(res.function_id)
            
        # 2. Graph Context (Neo4j)
        self.graph_store.connect()
        graph_context = self.graph_store.get_context_subgraph(function_ids)
        
        # 3. Directory Context (GraphRAG)
        # Get summaries for directories containing top files
        top_dirs = set()
        for func in candidate_functions:
            from pathlib import Path
            p = Path(func["file_path"]).parent
            top_dirs.add(str(p).replace('\\', '/'))
            
        all_summaries = self.graph_store.get_directory_summaries(repo_name)
        relevant_summaries = [s for s in all_summaries if s['path'] in top_dirs]
        
        return {
            "candidate_functions": candidate_functions,
            "graph_context": graph_context,
            "directory_context": relevant_summaries
        }

    def analyze_bug(self, state: GraphState) -> Dict[str, Any]:
        """Node: Analyze bug using LLM"""
        logger.info("Workflow Step: Analyzing Bug")
        
        # Combine directory summaries into graph context
        dir_context_str = "\nDirectory Summaries:\n"
        for s in state["directory_context"]:
            dir_context_str += f"- {s['path']}: {s['summary']}\n"
            
        full_graph_context = state["graph_context"] + "\n" + dir_context_str
        
        analysis_result = self.llm_service.analyze_issue(
            state["issue_title"],
            state["issue_body"],
            state["candidate_functions"],
            full_graph_context
        )
        
        return {
            "analysis": analysis_result.get("analysis", ""),
            "hypothesis": analysis_result.get("hypothesis", "")
        }

    def generate_patch(self, state: GraphState) -> Dict[str, Any]:
        """Node: Generate patch"""
        logger.info("Workflow Step: Generating Patch")
        
        # Identify target file from hypothesis or top candidate
        # For simplicity, we pick the top candidate if hypothesis is vague
        target_file = ""
        target_code = ""
        
        if state["candidate_functions"]:
            top_func = state["candidate_functions"][0]
            target_file = top_func["file_path"]
            target_code = top_func["snippet"]
            
        patch = self.llm_service.generate_patch(
            state["issue_title"],
            state["issue_body"],
            target_file,
            target_code,
            state["analysis"]
        )
        
        # Construct final result for the pipeline
        final_result = {
            "top_files": [{
                "file_path": f["file_path"],
                "score": f["score"],
                "functions": [f],
                "language": f["language"]
            } for f in state["candidate_functions"]],
            "llm_analysis": state["analysis"],
            "llm_hypothesis": state["hypothesis"],
            "llm_patch": patch,
            "repository": state["repo_name"]
        }
        
        return {
            "patch": patch,
            "final_result": final_result
        }

    def run(self, issue_title: str, issue_body: str, repo_name: str, repo_path: str) -> Dict[str, Any]:
        """Run the workflow"""
        initial_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "repo_name": repo_name,
            "repo_path": repo_path,
            "processed_issue": {},
            "candidate_functions": [],
            "graph_context": "",
            "directory_context": [],
            "analysis": "",
            "hypothesis": "",
            "patch": "",
            "final_result": {}
        }
        
        result = self.workflow.invoke(initial_state)
        return result["final_result"]
