"""
Workflow Manager - Orchestrates the bug localization process using LangGraph

Patch generation uses Chain-of-Thought reasoning based on:
- ThinkRepair (Yin et al., ISSTA 2024)
- SCoT (Li et al., TOSEM 2025)
"""

import logging
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
import operator

from .llm_service import LLMService
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
    generate_patch: bool  # Flag to enable/disable patch generation
    
    # Intermediate states
    processed_issue: Dict[str, Any]
    candidate_functions: List[Dict[str, Any]]
    graph_context: str
    directory_context: List[Dict[str, Any]]
    
    # Outputs
    analysis: str
    hypothesis: str
    patch: str
    patch_reasoning: Dict[str, Any]  # CoT reasoning from agent
    final_result: Dict[str, Any]

class WorkflowManager:
    """
    Manages the LangGraph workflow for bug localization.
    
    Patch generation is delegated to BugLocalizationAgent which implements 
    Chain-of-Thought reasoning based on ThinkRepair (Yin et al., ISSTA 2024).
    """
    
    def __init__(self):
        self.llm_service = LLMService()
        # self.bug_localization will be lazy initialized
        self.bug_localization = None
        
        self.workflow = self._build_graph()
        
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)
        
        # Define nodes - patch generation is now handled by the agent
        workflow.add_node("process_issue", self.process_issue)
        workflow.add_node("localize_bug", self.localize_bug)
        
        # Define edges
        workflow.set_entry_point("process_issue")
        workflow.add_edge("process_issue", "localize_bug")
        workflow.add_edge("localize_bug", END)
        
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
        """
        Node: Localize bug using Agentic RAG pipeline.
        
        If generate_patch is True, the agent will also generate a patch 
        using Chain-of-Thought reasoning (ThinkRepair methodology).
        """
        logger.info("Workflow Step: Localizing Bug (Agentic Pipeline)")
        
        generate_patch = state.get("generate_patch", False)
        
        # Agent.localize returns (selected_functions, all_candidates, token_usage, patch, patch_reasoning)
        selected_functions, _, _, patch, patch_reasoning = self.bug_localization.localize(
            state["issue_title"], 
            state["issue_body"],
            generate_patch=generate_patch
        )
        
        # Format concise analysis from top candidates (agent already provides analysis)
        analysis = ""
        ANALYSIS_LIMIT = 5
        top_candidates = selected_functions[:ANALYSIS_LIMIT]
        
        for idx, func in enumerate(top_candidates, 1):
            analysis += f"{idx}. `{func['name']}` in `{func.get('file_path', func.get('path'))}`\n"
            reason = func.get('analysis') or func.get('llm_reasoning', 'Selected as likely buggy function')
            analysis += f"   - {reason}\n\n"
        
        # Construct final result for the pipeline
        final_result = {
            "top_files": [{
                "file_path": f.get("file_path") or f.get("path", ""),
                "score": f.get("score", 0.0),
                "functions": [f],
                "language": "python"  # Assumption
            } for f in selected_functions],
            "llm_analysis": analysis,
            "llm_hypothesis": "",
            "llm_patch": patch,
            "patch_reasoning": patch_reasoning,
            "repository": state["repo_name"]
        }
            
        return {
            "candidate_functions": selected_functions,
            "analysis": analysis,
            "hypothesis": "",
            "patch": patch,
            "patch_reasoning": patch_reasoning,
            "final_result": final_result
        }

    def run(self, issue_title: str, issue_body: str, repo_name: str, repo_path: str, 
            generate_patch: bool = True) -> Dict[str, Any]:
        """
        Run the workflow.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body/description
            repo_name: Repository name
            repo_path: Path to the repository
            generate_patch: If True, generate a patch using CoT reasoning (default: True)
            
        Returns:
            Final result dictionary containing localization results and optional patch
        """
        initial_state = {
            "issue_title": issue_title,
            "issue_body": issue_body,
            "repo_name": repo_name,
            "repo_path": repo_path,
            "generate_patch": generate_patch,
            "processed_issue": {},
            "candidate_functions": [],
            "graph_context": "",
            "directory_context": [],
            "analysis": "",
            "hypothesis": "",
            "patch": "",
            "patch_reasoning": {},
            "final_result": {}
        }
        
        result = self.workflow.invoke(initial_state)
        return result["final_result"]
