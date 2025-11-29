"""
Integration Test for INSIGHT Tool Phase 2
Performs a full end-to-end test:
1. Sets up a dummy repository.
2. Indexes the repository (populating Neo4j and Vector Store).
3. Runs BugLocalization (triggering LangGraph, GraphRAG, and LLM).
4. Verifies the output structure and content.
"""

import os
import sys
import shutil
import logging
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Feature_Components.knowledgeBase import IndexRepository, BugLocalization
from Feature_Components.KnowledgeBase.graph_store import GraphStore
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integration_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEST_REPO_ROOT = Path("test_repos/integration_test_repo")
TEST_REPO_NAME = "test_user/integration_test_repo"

def setup_dummy_repo():
    """Create a dummy repository with some code"""
    if TEST_REPO_ROOT.exists():
        shutil.rmtree(TEST_REPO_ROOT)
    TEST_REPO_ROOT.mkdir(parents=True)
    
    # Create src directory
    src_dir = TEST_REPO_ROOT / "src"
    src_dir.mkdir()
    
    # Create main.py
    with open(src_dir / "main.py", "w") as f:
        f.write("""
def main():
    print("Starting application...")
    result = calculate_sum(5, 10)
    print(f"Result: {result}")

def calculate_sum(a, b):
    return a + b
""")

    # Create utils.py with a "bug"
    with open(src_dir / "utils.py", "w") as f:
        f.write("""
def divide_numbers(a, b):
    # Bug: No check for division by zero
    return a / b

def multiply_numbers(a, b):
    return a * b
""")

    logger.info(f"Created dummy repo at {TEST_REPO_ROOT}")

def test_indexing():
    """Test the indexing process"""
    logger.info("Step 1: Indexing Repository...")
    
    # Clear existing data for this repo
    store = GraphStore()
    store.connect()
    store.clear_database(TEST_REPO_NAME)
    store.close()
    
    # Run Indexing
    result = IndexRepository(
        repo_path=str(TEST_REPO_ROOT),
        repo_name=TEST_REPO_NAME
    )
    
    if not result['success']:
        logger.error(f"Indexing failed: {result.get('error')}")
        return False
        
    logger.info("Indexing successful!")
    logger.info(f"Stats: {result}")
    
    # Verify GraphRAG (Directory Summaries)
    store = GraphStore()
    store.connect()
    summaries = store.get_directory_summaries(TEST_REPO_NAME)
    store.close()
    
    logger.info(f"Found {len(summaries)} directory summaries")
    if len(summaries) == 0:
        logger.warning("No directory summaries found! (GraphRAG might be failing or LLM unavailable)")
    else:
        for s in summaries:
            logger.info(f"Summary for {s['path']}: {s['summary'][:50]}...")
            
    return True

def test_bug_localization():
    """Test the bug localization pipeline"""
    logger.info("Step 2: Running Bug Localization...")
    
    issue_title = "Division by zero error"
    issue_body = "The application crashes when dividing by zero in the utils module. We need to add a check."
    
    result = BugLocalization(
        issue_title=issue_title,
        issue_body=issue_body,
        repo_owner="test_user",
        repo_name="integration_test_repo",
        repo_path=str(TEST_REPO_ROOT)
    )
    
    if 'error' in result:
        logger.error(f"Bug Localization failed: {result['error']}")
        return False
        
    logger.info("Bug Localization successful!")
    
    # Verify Outputs
    top_files = result.get('top_files', [])
    logger.info(f"Top Files Found: {len(top_files)}")
    for f in top_files:
        logger.info(f"- {f['file_path']}")
        
    # Verify LLM Analysis
    llm_analysis = result.get('llm_analysis')
    llm_patch = result.get('llm_patch')
    
    logger.info(f"LLM Analysis: {llm_analysis[:100] if llm_analysis else 'None'}")
    logger.info(f"LLM Patch: {llm_patch[:100] if llm_patch else 'None'}")
    
    if not llm_analysis or not llm_patch:
        logger.warning("LLM Analysis or Patch is missing! (LLM might be unavailable)")
        return False
        
    return True

if __name__ == "__main__":
    try:
        setup_dummy_repo()
        if test_indexing():
            if test_bug_localization():
                logger.info("INTEGRATION TEST PASSED")
            else:
                logger.error("INTEGRATION TEST FAILED at Bug Localization")
        else:
            logger.error("INTEGRATION TEST FAILED at Indexing")
    except Exception as e:
        logger.error(f"Integration Test Exception: {e}", exc_info=True)
