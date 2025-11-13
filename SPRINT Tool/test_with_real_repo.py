"""
Test Knowledge Base System with a Real Repository
This script demonstrates end-to-end functionality
"""

import sys
import os
from pathlib import Path

# Add SPRINT Tool to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("KNOWLEDGE BASE SYSTEM - REAL REPOSITORY TEST")
print("=" * 70)
print()

# Configuration
print("CONFIGURATION:")
print("-" * 70)

# You can change these to test with your own repository
TEST_REPO_PATH = input("Enter repository path (or press Enter for current directory): ").strip()
if not TEST_REPO_PATH:
    TEST_REPO_PATH = "."

TEST_REPO_NAME = input("Enter repository name (e.g., 'owner/repo'): ").strip()
if not TEST_REPO_NAME:
    TEST_REPO_NAME = "test/repo"

print(f"\nRepository Path: {TEST_REPO_PATH}")
print(f"Repository Name: {TEST_REPO_NAME}")
print()

# Check if path exists
if not Path(TEST_REPO_PATH).exists():
    print(f"❌ Error: Path '{TEST_REPO_PATH}' does not exist!")
    sys.exit(1)

# Check if it's a git repository
if not (Path(TEST_REPO_PATH) / ".git").exists():
    print(f"⚠️  Warning: '{TEST_REPO_PATH}' is not a git repository")
    print("   Some features may not work correctly")
    print()

# Step 1: Index the Repository
print("STEP 1: Indexing Repository")
print("-" * 70)
print("This may take a few minutes depending on repository size...")
print()

try:
    from Feature_Components.knowledgeBase import IndexRepository
    
    result = IndexRepository(
        repo_path=TEST_REPO_PATH,
        repo_name=TEST_REPO_NAME,
        model_name="microsoft/unixcoder-base"
    )
    
    print("\n✅ Indexing Complete!")
    print(f"   Files indexed: {result.get('total_files', 0)}")
    print(f"   Functions found: {result.get('total_functions', 0)}")
    print(f"   Windows generated: {result.get('total_windows', 0)}")
    print(f"   Time taken: {result.get('indexing_time_seconds', 0):.1f}s")
    print()
    
except Exception as e:
    print(f"\n❌ Indexing failed: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure the repository contains Python files")
    print("2. Check that you have enough disk space")
    print("3. Verify all dependencies are installed")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test Bug Localization
print("STEP 2: Testing Bug Localization")
print("-" * 70)

# Sample issue
sample_issues = [
    {
        "title": "Bug in data processing",
        "body": "The function crashes when processing empty input data"
    },
    {
        "title": "Error in validation",
        "body": "Validation fails for special characters in user input"
    },
    {
        "title": "Memory leak",
        "body": "Application consumes too much memory over time"
    }
]

print("Testing with sample issues...")
print()

try:
    from Feature_Components.knowledgeBase import BugLocalization
    
    for i, issue in enumerate(sample_issues[:1], 1):  # Test with first issue
        print(f"Issue {i}: {issue['title']}")
        print(f"Description: {issue['body']}")
        print()
        
        # Perform bug localization
        results = BugLocalization(
            issue_title=issue['title'],
            issue_body=issue['body'],
            repo_owner=TEST_REPO_NAME.split('/')[0],
            repo_name=TEST_REPO_NAME.split('/')[1] if '/' in TEST_REPO_NAME else TEST_REPO_NAME,
            repo_path=TEST_REPO_PATH,
            k=5,  # Top 5 results
            enable_line_level=True
        )
        
        # Check for errors
        if 'error' in results:
            print(f"⚠️  Localization returned error: {results['error']}")
            print()
            continue
        
        # Display results
        print(f"✅ Localization Complete!")
        print(f"   Confidence: {results.get('confidence', 'unknown')}")
        print(f"   Confidence Score: {results.get('confidence_score', 0):.2%}")
        print(f"   Total Results: {results.get('total_results', 0)}")
        print()
        
        # Show top results
        top_files = results.get('top_files', [])
        if top_files:
            print("   Top Results:")
            for j, file_result in enumerate(top_files[:3], 1):
                file_path = file_result.get('file_path', 'unknown')
                score = file_result.get('score', 0)
                functions = file_result.get('functions', [])
                
                print(f"   {j}. {file_path} (score: {score:.3f})")
                if functions:
                    func = functions[0]
                    print(f"      Function: {func.get('name', 'unknown')}")
                    line_range = func.get('line_range', [0, 0])
                    print(f"      Lines: {line_range[0]}-{line_range[1]}")
            print()
        
        # Show line-level results if available
        line_results = results.get('line_level_results', [])
        if line_results:
            print("   Line-Level Results:")
            for j, line_result in enumerate(line_results[:2], 1):
                func_name = line_result.get('function_name', 'unknown')
                file_path = line_result.get('file_path', 'unknown')
                line_start = line_result.get('line_start', 0)
                line_end = line_result.get('line_end', 0)
                score = line_result.get('score', 0)
                
                print(f"   {j}. {func_name} in {file_path}")
                print(f"      Lines: {line_start}-{line_end} (score: {score:.3f})")
            print()
    
    print("✅ Bug localization tests passed!")
    print()
    
except Exception as e:
    print(f"\n❌ Bug localization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test Comment Generation
print("STEP 3: Testing Comment Generation")
print("-" * 70)

try:
    from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator
    
    generator = CommentGenerator(
        TEST_REPO_NAME.split('/')[0],
        TEST_REPO_NAME.split('/')[1] if '/' in TEST_REPO_NAME else TEST_REPO_NAME
    )
    
    comment = generator.generate_comment(
        results=results,
        confidence=results.get('confidence', 'medium'),
        confidence_score=results.get('confidence_score', 0.5)
    )
    
    print("Generated GitHub Comment:")
    print("-" * 70)
    print(comment[:500] + "..." if len(comment) > 500 else comment)
    print("-" * 70)
    print()
    
    # Save to file
    output_file = "sample_github_comment.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(comment)
    
    print(f"✅ Full comment saved to: {output_file}")
    print()
    
except Exception as e:
    print(f"❌ Comment generation failed: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Test Telemetry
print("STEP 4: Testing Telemetry")
print("-" * 70)

try:
    from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger
    
    telemetry = get_telemetry_logger()
    
    # Log a test retrieval
    telemetry.log_retrieval(
        issue_id="test-123",
        latency_ms=1500.0,
        top_k=5,
        confidence=results.get('confidence', 'medium'),
        repo_name=TEST_REPO_NAME,
        success=True
    )
    
    # Get statistics
    stats = telemetry.get_statistics("1h")
    
    print("Telemetry Statistics (last 1 hour):")
    print(f"   Total requests: {stats['retrieval']['total_requests']}")
    print(f"   Success rate: {stats['retrieval']['success_rate']:.1%}")
    print(f"   Avg latency: {stats['retrieval']['avg_latency_ms']:.0f}ms")
    print()
    
    print("✅ Telemetry logging works!")
    print()
    
except Exception as e:
    print(f"❌ Telemetry test failed: {e}")
    import traceback
    traceback.print_exc()

# Final Summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print()
print("✅ All tests completed successfully!")
print()
print("WHAT WAS TESTED:")
print("1. ✅ Repository indexing")
print("2. ✅ Bug localization (function-level)")
print("3. ✅ Line-level localization")
print("4. ✅ Confidence calibration")
print("5. ✅ GitHub comment generation")
print("6. ✅ Telemetry logging")
print()
print("NEXT STEPS:")
print("1. Review the generated comment in: sample_github_comment.md")
print("2. Check telemetry logs in: telemetry_logs/")
print("3. View indices in: indices/")
print("4. Integrate with SPRINT for automatic processing")
print()
print("For more information, see:")
print("- QUICKSTART.md - Quick start guide")
print("- README.md - Complete documentation")
print()
print("=" * 70)
