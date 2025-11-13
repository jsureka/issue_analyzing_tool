"""
Simple test of Knowledge Base with buggy test_python_repo
Uses the main API functions
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

# Import main API
try:
    from Feature_Components.knowledgeBase import IndexRepository, BugLocalization, GetIndexStatus
    print("✅ Knowledge Base API imported successfully\n")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Setup paths
repo_path = os.path.join(Path(__file__).parent.parent, "test_python_repo")
repo_name = "test/python_repo"

print(f"Repository path: {repo_path}")
print(f"Repository exists: {os.path.exists(repo_path)}\n")

if not os.path.exists(repo_path):
    print("❌ test_python_repo not found!")
    sys.exit(1)

# Step 1: Check if already indexed
print("=" * 80)
print("STEP 1: Check Index Status")
print("=" * 80)

status = GetIndexStatus(repo_name)
print(f"Indexed: {status.get('indexed', False)}")

if not status.get('indexed', False):
    print("\nIndexing repository...")
    print("(This may take a few minutes...)\n")
    
    # Index the repository
    index_result = IndexRepository(
        repo_path=repo_path,
        repo_name=repo_name
    )
    
    if index_result.get('success'):
        print("✅ Repository indexed successfully!")
        print(f"   Total files: {index_result.get('total_files', 0)}")
        print(f"   Total functions: {index_result.get('total_functions', 0)}")
        print(f"   Indexing time: {index_result.get('indexing_time_seconds', 0):.2f}s")
    else:
        print(f"❌ Indexing failed: {index_result.get('error', 'Unknown error')}")
        sys.exit(1)
else:
    print("✅ Repository already indexed")
    print(f"   Total functions: {status.get('total_functions', 'N/A')}")

# Step 2: Test bug localization queries
print("\n" + "=" * 80)
print("STEP 2: Test Bug Localization Queries")
print("=" * 80)

test_issues = [
    {
        "title": "Division by Zero in Character Damage Calculation",
        "body": "When a character takes damage and the defense value equals the damage value, "
                "the game crashes with a division by zero error. This happens in the take_damage "
                "method of the Character class."
    },
    {
        "title": "Game Freezes When Character Levels Up",
        "body": "The game becomes unresponsive when a character gains enough experience to level up. "
                "It seems to be stuck in an infinite loop in the experience gain system."
    },
    {
        "title": "Shop Allows Buying Items with Full Inventory",
        "body": "Players can purchase items from shops even when their inventory is full, "
                "which causes the inventory to exceed its maximum size limit."
    },
    {
        "title": "Inventory Can Hold One Extra Item",
        "body": "The inventory system allows adding one more item than the specified max_size. "
                "For example, with max_size=20, players can actually hold 21 items."
    },
    {
        "title": "Quest System Crashes on Invalid Objective Index",
        "body": "When updating quest objectives with an invalid index, the game crashes with an "
                "IndexError. There's no bounds checking in the update_objective method."
    }
]

for i, issue in enumerate(test_issues, 1):
    print(f"\n{'-' * 80}")
    print(f"TEST {i}: {issue['title']}")
    print(f"{'-' * 80}")
    
    try:
        result = BugLocalization(
            issue_title=issue['title'],
            issue_body=issue['body'],
            repo_owner="test",
            repo_name="python_repo",
            repo_path=repo_path,
            k=5,
            enable_line_level=False  # Disable for faster testing
        )
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Found {result.get('total_results', 0)} results")
            print(f"   Confidence: {result.get('confidence', 'N/A')}")
            
            top_files = result.get('top_files', [])
            if top_files:
                print(f"\n   Top {min(3, len(top_files))} files:")
                for j, file_info in enumerate(top_files[:3], 1):
                    print(f"   {j}. {file_info.get('file_path', 'N/A')} "
                          f"(score: {file_info.get('score', 0):.4f})")
                    
                    functions = file_info.get('functions', [])
                    if functions:
                        func = functions[0]
                        print(f"      → {func.get('function_name', 'N/A')} "
                              f"(lines {func.get('start_line', 0)}-{func.get('end_line', 0)})")
    
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
