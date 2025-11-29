"""
Verification Script for INSIGHT Tool Phase 2
Tests:
1. LLM Service connectivity
2. GraphStore directory nodes
3. WorkflowManager execution
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Feature_Components.KnowledgeBase.llm_service import LLMService
from Feature_Components.KnowledgeBase.graph_store import GraphStore
from Feature_Components.KnowledgeBase.workflow_manager import WorkflowManager
from Feature_Components.knowledgeBase import BugLocalization

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("verify.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_llm_service():
    logger.info("Testing LLM Service...")
    llm = LLMService()
    if not llm.is_available():
        logger.warning("LLM Service not available (check API Key)")
        return False
    
    summary = llm.summarize_code("def hello():\n    print('Hello World')", "test.py")
    logger.info(f"Summary: {summary}")
    return True

def test_graph_store():
    logger.info("Testing GraphStore...")
    store = GraphStore()
    if not store.connect():
        logger.error("Failed to connect to Neo4j")
        return False
        
    # Create test directory node
    store.create_directory_node("test_dir", "test_repo", "src/test", "Test Summary")
    
    # Retrieve summaries
    summaries = store.get_directory_summaries("test_repo")
    logger.info(f"Summaries: {summaries}")
    
    return len(summaries) > 0

def test_workflow():
    logger.info("Testing WorkflowManager...")
    # This requires an indexed repo. We'll mock the run or try to run on a dummy if possible.
    # For now, we just instantiate to check imports and graph construction.
    try:
        wm = WorkflowManager()
        logger.info("WorkflowManager initialized successfully")
        return True
    except Exception as e:
        logger.error(f"WorkflowManager init failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Verification...")
    
    llm_ok = test_llm_service()
    graph_ok = test_graph_store()
    workflow_ok = test_workflow()
    
    if llm_ok and graph_ok and workflow_ok:
        logger.info("ALL CHECKS PASSED")
    else:
        logger.error("SOME CHECKS FAILED")
