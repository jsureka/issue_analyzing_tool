"""Simple test runner for Knowledge Base"""
import sys
import os

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sprint_tool_dir = os.path.join(current_dir, 'SPRINT Tool')

# Add SPRINT Tool to path so we can import Feature_Components as a package
sys.path.insert(0, sprint_tool_dir)

print(f"Current directory: {current_dir}")
print(f"SPRINT Tool directory: {sprint_tool_dir}")

try:
    from Feature_Components.knowledgeBase import KnowledgeBase
    print("\n✓ Successfully imported KnowledgeBase")
    
    # Test with test_python_repo
    repo_path = os.path.join(current_dir, "test_python_repo")
    print(f"\nInitializing KB with repo: {repo_path}")
    
    kb = KnowledgeBase(repo_path=repo_path)
    print("✓ KnowledgeBase initialized")
    
    print("\nBuilding knowledge base...")
    kb.build_knowledge_base()
    print("✓ Knowledge base built")
    
    # Test query
    print("\n" + "="*60)
    print("TEST QUERY 1: Character damage calculation")
    print("="*60)
    query = "How does the take_damage method work?"
    result = kb.query(query)
    print(f"\nQuery: {query}")
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources: {result['sources']}")
    
    print("\n" + "="*60)
    print("TEST QUERY 2: Experience system")
    print("="*60)
    query2 = "What happens when a character gains experience?"
    result2 = kb.query(query2)
    print(f"\nQuery: {query2}")
    print(f"\nAnswer:\n{result2['answer']}")
    print(f"\nSources: {result2['sources']}")
    
    print("\n✓ All tests completed successfully!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
