"""
Test script to verify Knowledge Base system can identify bugs in test_python_repo
"""

import sys
import os

# Add SPRINT Tool to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SPRINT Tool'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SPRINT Tool', 'Feature_Components'))

from knowledgeBase import KnowledgeBase

def test_bug_detection():
    """Test if KB can help identify bugs in the codebase"""
    
    print("=" * 80)
    print("TESTING KNOWLEDGE BASE WITH BUGGY CODE")
    print("=" * 80)
    
    # Initialize Knowledge Base
    kb = KnowledgeBase(repo_path="test_python_repo")
    
    print("\n[1] Building knowledge base...")
    kb.build_knowledge_base()
    
    print("\n[2] Testing bug-related queries...")
    
    # Test 1: Division by zero bug in character.py
    print("\n" + "-" * 80)
    print("TEST 1: Query about damage calculation")
    print("-" * 80)
    query1 = "How does the take_damage method work in the Character class?"
    result1 = kb.query(query1)
    print(f"Query: {query1}")
    print(f"Response: {result1['answer']}")
    print(f"Sources: {result1['sources']}")
    
    # Test 2: Infinite loop bug
    print("\n" + "-" * 80)
    print("TEST 2: Query about experience and leveling")
    print("-" * 80)
    query2 = "What happens when a character gains experience?"
    result2 = kb.query(query2)
    print(f"Query: {query2}")
    print(f"Response: {result2['answer']}")
    print(f"Sources: {result2['sources']}")
    
    # Test 3: Missing validation bug
    print("\n" + "-" * 80)
    print("TEST 3: Query about shop purchases")
    print("-" * 80)
    query3 = "What checks are performed when buying an item from a shop?"
    result3 = kb.query(query3)
    print(f"Query: {query3}")
    print(f"Response: {result3['answer']}")
    print(f"Sources: {result3['sources']}")
    
    # Test 4: Off-by-one error
    print("\n" + "-" * 80)
    print("TEST 4: Query about inventory limits")
    print("-" * 80)
    query4 = "How does the inventory check if it's full?"
    result4 = kb.query(query4)
    print(f"Query: {query4}")
    print(f"Response: {result4['answer']}")
    print(f"Sources: {result4['sources']}")
    
    # Test 5: Missing bounds check
    print("\n" + "-" * 80)
    print("TEST 5: Query about quest objectives")
    print("-" * 80)
    query5 = "How are quest objectives updated?"
    result5 = kb.query(query5)
    print(f"Query: {query5}")
    print(f"Response: {result5['answer']}")
    print(f"Sources: {result5['sources']}")
    
    # Test 6: Logic error in combat
    print("\n" + "-" * 80)
    print("TEST 6: Query about combat turn order")
    print("-" * 80)
    query6 = "How is turn order determined in combat?"
    result6 = kb.query(query6)
    print(f"Query: {query6}")
    print(f"Response: {result6['answer']}")
    print(f"Sources: {result6['sources']}")
    
    # Test 7: Cross-file relationship query
    print("\n" + "-" * 80)
    print("TEST 7: Query about class relationships")
    print("-" * 80)
    query7 = "What is the relationship between Player, Character, and NPC classes?"
    result7 = kb.query(query7)
    print(f"Query: {query7}")
    print(f"Response: {result7['answer']}")
    print(f"Sources: {result7['sources']}")
    
    # Test 8: Complex system query
    print("\n" + "-" * 80)
    print("TEST 8: Query about combat system")
    print("-" * 80)
    query8 = "Explain how the combat system works from start to finish"
    result8 = kb.query(query8)
    print(f"Query: {query8}")
    print(f"Response: {result8['answer']}")
    print(f"Sources: {result8['sources']}")
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    
    # Summary of bugs introduced
    print("\n" + "=" * 80)
    print("BUGS INTRODUCED IN TEST REPO:")
    print("=" * 80)
    print("1. character.py - take_damage(): Division by zero when defense equals damage")
    print("2. character.py - gain_experience(): Infinite loop, doesn't consume experience")
    print("3. utils.py - calculate_percentage(): Returns 100.0 instead of 0.0 when total is 0")
    print("4. world.py - travel(): Missing connection validation, allows teleportation")
    print("5. shop.py - buy_item(): Missing inventory space check, can overflow")
    print("6. save_system.py - auto_save(): Accesses non-existent attribute on base class")
    print("7. inventory.py - add_item(): Off-by-one error, allows one extra item")
    print("8. combat.py - _determine_turn_order(): Always returns same order")
    print("9. quest.py - update_objective(): Missing bounds check, can cause IndexError")
    print("=" * 80)


if __name__ == "__main__":
    test_bug_detection()
