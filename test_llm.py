import os
import logging
from dotenv import load_dotenv
import sys
sys.path.append(os.path.join(os.getcwd(), "INSIGHT Tool"))
from Feature_Components.KnowledgeBase.llm_service import LLMService

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load env
load_dotenv("INSIGHT Tool/.env")

def test_llm():
    print("Initializing LLM Service...")
    llm = LLMService()
    
    if not llm.is_available():
        print("LLM Service NOT available. Check API Key.")
        return

    print("LLM Service available.")
    
    candidates = [
        {
            "id": "1",
            "name": "test_func",
            "file_path": "test.py",
            "code": "def test_func():\n    print('hello world')\n    return True",
            "score": 0.5
        },
        {
            "id": "2",
            "name": "buggy_func",
            "file_path": "bug.py",
            "code": "def buggy_func():\n    raise Exception('bug')",
            "score": 0.4
        }
    ]
    
    print("Testing re-ranking...")
    reranked = llm.rerank_candidates(
        "Fix bug in buggy_func",
        "The buggy_func raises an exception.",
        candidates
    )
    
    print("Reranked results:")
    for c in reranked:
        print(f"ID: {c['id']}, Score: {c.get('final_score', c['score'])}, LLM Score: {c.get('llm_score')}")

if __name__ == "__main__":
    test_llm()
