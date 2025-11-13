"""
Test Knowledge Base with buggy test_python_repo
"""

import sys
import os
from pathlib import Path

# Add SPRINT Tool to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("TESTING KNOWLEDGE BASE WITH BUGGY CODE REPOSITORY")
print("=" * 80)
print()

# Import components
try:
    from Feature_Components.KnowledgeBase.embedder import CodeEmbedder
    from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer
    from Feature_Components.KnowledgeBase.retriever import DenseRetriever
    from Feature_Components.KnowledgeBase.formatter import ResultFormatter
    print("✅ All components imported successfully\n")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Setup paths
repo_path = os.path.join(Path(__file__).parent.parent, "test_python_repo")
print(f"Repository path: {repo_path}")
print(f"Repository exists: {os.path.exists(repo_path)}\n")

if not os.path.exists(repo_path):
    print("❌ test_python_repo not found!")
    sys.exit(1)

print("=" * 80)
print("STEP 1: Initialize Components")
print("=" * 80)

try:
    embedder = CodeEmbedder()
    print("✅ CodeEmbedder initialized")
    
    indexer = RepositoryIndexer(embedder)
    print("✅ RepositoryIndexer initialized")
    
    retriever = DenseRetriever(embedder)
    print("✅ DenseRetriever initialized")
    
    formatter = ResultFormatter()
    print("✅ ResultFormatter initialized")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 2: Index Repository")
print("=" * 80)

try:
    print(f"Indexing repository: {repo_path}")
    vector_store = indexer.index_repository(repo_path)
    print(f"✅ Repository indexed successfully")
    print(f"   Total chunks: {len(vector_store.chunks)}")
    print(f"   Files indexed: {len(set(chunk['file_path'] for chunk in vector_store.chunks))}")
except Exception as e:
    print(f"❌ Indexing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 3: Test Queries on Buggy Code")
print("=" * 80)

test_queries = [
    {
        "title": "Division by Zero Bug",
        "query": "How does the take_damage method calculate damage in the Character class?"
    },
    {
        "title": "Infinite Loop Bug",
        "query": "What happens when a character gains experience and levels up?"
    },
    {
        "title": "Missing Validation",
        "query": "What validations are performed when buying an item from a shop?"
    },
    {
        "title": "Off-by-One Error",
        "query": "How does the inventory check if it's full before adding items?"
    },
    {
        "title": "Missing Bounds Check",
        "query": "How are quest objectives updated and what validation is done?"
    },
    {
        "title": "Logic Error",
        "query": "How is turn order determined in combat between two characters?"
    },
    {
        "title": "Class Relationships",
        "query": "What is the inheritance hierarchy between Player, Character, and NPC?"
    }
]

for i, test in enumerate(test_queries, 1):
    print(f"\n{'-' * 80}")
    print(f"QUERY {i}: {test['title']}")
    print(f"{'-' * 80}")
    print(f"Question: {test['query']}\n")
    
    try:
        # Retrieve relevant code
        results = retriever.retrieve(test['query'], vector_store, top_k=5)
        
        print(f"Found {len(results)} relevant code chunks:\n")
        
        for j, result in enumerate(results[:3], 1):  # Show top 3
            print(f"  Result {j} (Score: {result['score']:.4f}):")
            print(f"    File: {result['file_path']}")
            print(f"    Lines: {result['start_line']}-{result['end_line']}")
            print(f"    Code preview: {result['code'][:100]}...")
            print()
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("BUGS INTRODUCED IN TEST REPOSITORY:")
print("=" * 80)
print("""
1. character.py - take_damage(): Division by zero when defense equals damage
2. character.py - gain_experience(): Infinite loop, doesn't consume experience  
3. utils.py - calculate_percentage(): Returns 100.0 instead of 0.0 when total is 0
4. world.py - travel(): Missing connection validation, allows teleportation
5. shop.py - buy_item(): Missing inventory space check, can overflow
6. save_system.py - auto_save(): Accesses non-existent attribute on base class
7. inventory.py - add_item(): Off-by-one error, allows one extra item
8. combat.py - _determine_turn_order(): Always returns same order
9. quest.py - update_objective(): Missing bounds check, can cause IndexError
""")

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
