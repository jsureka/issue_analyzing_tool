"""
Workflow Manager - Orchestrates the bug localization process using LangGraph
"""

import logging
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
import operator
import os

from .llm_service import LLMService
from .retriever import DenseRetriever
from .graph_store import GraphStore
from .issue_processor import IssueProcessor

# Try to import Config from correct location
try:
    from ...config import Config
except ImportError:
    try:
        from config import Config
    except ImportError:
        # Fallback
        class Config:
            LLM_SELECTION_COUNT = 3

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
        # self.bug_localization will be lazy initialized
        self.bug_localization = None
        
        self.workflow = self._build_graph()
        
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)
        
        # Define nodes
        workflow.add_node("process_issue", self.process_issue)
        workflow.add_node("localize_bug", self.localize_bug)
        workflow.add_node("generate_patch", self.generate_patch)
        
        # Define edges
        workflow.set_entry_point("process_issue")
        workflow.add_edge("process_issue", "localize_bug")
        workflow.add_edge("localize_bug", "generate_patch")
        workflow.add_edge("generate_patch", END)
        
        return workflow.compile()
        
    def process_issue(self, state: GraphState) -> Dict[str, Any]:
        """Node: Process the issue text"""
        logger.info("Workflow Step: Processing Issue")
        
        # Initialize BugLocalizationAgent if needed
        if not self.bug_localization or self.bug_localization.repo_name != state["repo_name"]:
            from ..Agent.agent import BugLocalizationAgent
            self.bug_localization = BugLocalizationAgent(state["repo_name"], state["repo_path"])
            
        return {"processed_issue": {}}

    def localize_bug(self, state: GraphState) -> Dict[str, Any]:
        """Node: Localize bug using Agentic RAG pipeline"""
        logger.info("Workflow Step: Localizing Bug (Agentic Pipeline)")
        
        # Agent.localize returns (selected_functions, all_candidates, token_usage)
        selected_functions, _, _ = self.bug_localization.localize(
            state["issue_title"], 
            state["issue_body"]
        )
        
        # Format concise analysis from top candidates (agent already provides analysis)
        analysis = ""
        ANALYSIS_LIMIT = 3
        top_candidates = selected_functions[:ANALYSIS_LIMIT]
        
        for idx, func in enumerate(top_candidates, 1):
            analysis += f"{idx}. `{func['name']}` in `{func.get('file_path', func.get('path'))}`\n"
            reason = func.get('analysis') or func.get('llm_reasoning', 'Selected as likely buggy function')
            analysis += f"   - {reason}\n\n"
            
        return {
            "candidate_functions": selected_functions,
            "analysis": analysis,
            "hypothesis": "" 
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
            target_file = top_func.get("file_path") or top_func.get("path") or ""
            target_code = top_func.get("code", "")
            
            # If code is missing (likely finding from index), read from disk
            if not target_code and target_file and state.get("repo_path"):
                 try:
                     # target_file might be relative or absolute. 
                     # Indexer stores relative paths usually.
                     full_path = target_file
                     if not os.path.isabs(target_file):
                          full_path = os.path.join(state["repo_path"], target_file)
                     
                     if os.path.exists(full_path):
                         with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                             target_code = f.read()
                 except Exception as e:
                     logger.warning(f"Failed to read target file {target_file} for patch generation: {e}")

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
                "score": f.get("score", 0.0),
                "functions": [f],
                "language": "python" # Assumption
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
