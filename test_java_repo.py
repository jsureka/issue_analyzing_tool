"""
Test script for Java repository indexing and bug localization
Tests the multi-language support with WheelOfFortune Java repository
"""

import sys
import os
import time

# Add SPRINT Tool to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SPRINT Tool'))

from Feature_Components.knowledgeBase import IndexRepository, BugLocalization, GetIndexStatus

def test_java_indexing():
    """Test indexing a Java repository"""
    print("=" * 80)
    print("TEST 1: Indexing Java Repository")
    print("=" * 80)
    
    repo_path = "WheelOfFortune-master"
    repo_name = "test/WheelOfFortune"
    
    print(f"\nIndexing repository: {repo_path}")
    print(f"Repository name: {repo_name}")
    
    try:
        start_time = time.time()
        
        result = IndexRepository(
            repo_path=repo_path,
            repo_name=repo_name,
            model_name="microsoft/unixcoder-base"
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Indexing completed in {elapsed:.2f} seconds")
        print(f"\nIndexing Results:")
        print(f"  - Total files: {result.get('total_files', 0)}")
        print(f"  - Total functions: {result.get('total_functions', 0)}")
        print(f"  - Commit SHA: {result.get('commit_sha', 'unknown')}")
        print(f"  - Index path: {result.get('index_path', 'N/A')}")
        
        # Check for language statistics if available
        if 'languages' in result:
            print(f"\n  Language Statistics:")
            for lang, count in result['languages'].items():
                print(f"    - {lang}: {count} files")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Indexing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_java_bug_localization():
    """Test bug localization on Java repository"""
    print("\n" + "=" * 80)
    print("TEST 2: Bug Localization on Java Code")
    print("=" * 80)
    
    repo_path = "WheelOfFortune-master"
    repo_name = "test/WheelOfFortune"
    
    # Test issue about the Wheel class
    issue_title = "Wheel spin method not working correctly"
    issue_body = """
    The wheel spin functionality seems to have issues. When I call the spin() method,
    the wheel value is not being set properly. The setWheelValue() and setWheelSpot()
    methods might have bugs. Also, the wheelValue() method that calculates the value
    based on the spot might be returning incorrect values.
    """
    
    print(f"\nIssue Title: {issue_title}")
    print(f"Issue Body: {issue_body[:100]}...")
    
    try:
        start_time = time.time()
        
        results = BugLocalization(
            issue_title=issue_title,
            issue_body=issue_body,
            repo_owner="test",
            repo_name="WheelOfFortune",
            repo_path=repo_path,
            k=10,
            enable_line_level=False  # Disable for faster testing
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Bug localization completed in {elapsed:.2f} seconds")
        
        if 'error' in results:
            print(f"\n❌ Error: {results['error']}")
            return False
        
        print(f"\nResults:")
        print(f"  - Total results: {results.get('total_results', 0)}")
        print(f"  - Confidence: {results.get('confidence', 'N/A')}")
        print(f"  - Confidence score: {results.get('confidence_score', 0):.2%}")
        
        print(f"\nTop 5 Candidate Functions:")
        top_files = results.get('top_files', [])
        
        rank = 1
        for file_data in top_files[:5]:
            file_path = file_data.get('file_path', '')
            language = file_data.get('language', 'unknown')
            functions = file_data.get('functions', [])
            
            for func in functions[:2]:  # Top 2 functions per file
                if rank > 5:
                    break
                    
                func_name = func.get('name', 'unknown')
                score = func.get('score', 0.0)
                line_range = func.get('line_range', [0, 0])
                func_language = func.get('language', language)
                
                print(f"\n  {rank}. {func_name} in {file_path}")
                print(f"     Language: {func_language}")
                print(f"     Score: {score:.3f}")
                print(f"     Lines: {line_range[0]}-{line_range[1]}")
                
                rank += 1
            
            if rank > 5:
                break
        
        return True
        
    except Exception as e:
        print(f"\n❌ Bug localization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_index_status():
    """Test getting index status"""
    print("\n" + "=" * 80)
    print("TEST 3: Check Index Status")
    print("=" * 80)
    
    repo_name = "test/WheelOfFortune"
    
    try:
        status = GetIndexStatus(repo_name)
        
        if status and status.get('indexed'):
            print(f"\n✅ Repository is indexed")
            print(f"\nIndex Status:")
            print(f"  - Total functions: {status.get('total_functions', 0)}")
            print(f"  - Index path: {status.get('index_path', 'N/A')}")
            return True
        else:
            print(f"\n❌ Repository is not indexed")
            return False
            
    except Exception as e:
        print(f"\n❌ Status check failed: {e}")
        return False


def test_mixed_language_detection():
    """Test language detection on Java files"""
    print("\n" + "=" * 80)
    print("TEST 4: Language Detection")
    print("=" * 80)
    
    from Feature_Components.KnowledgeBase.parser_factory import ParserFactory, LanguageDetector
    
    factory = ParserFactory()
    detector = LanguageDetector(factory)
    
    test_files = [
        "Wheel.java",
        "GameBoard.java",
        "Main.java",
        "example.py",
        "test.js"
    ]
    
    print("\nTesting language detection:")
    for file in test_files:
        language = detector.detect_language(file)
        is_supported = detector.is_supported(file)
        
        status = "✅ Supported" if is_supported else "❌ Not supported"
        print(f"  {file:20} → {language or 'unknown':10} {status}")
    
    # Test supported languages
    supported = factory.get_supported_languages()
    extensions = factory.get_supported_extensions()
    
    print(f"\nSupported languages: {', '.join(supported)}")
    print(f"Supported extensions: {', '.join(extensions)}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("JAVA REPOSITORY TESTING - Multi-Language Support")
    print("=" * 80)
    
    results = []
    
    # Test 1: Language Detection
    print("\n")
    results.append(("Language Detection", test_mixed_language_detection()))
    
    # Test 2: Indexing
    print("\n")
    results.append(("Java Repository Indexing", test_java_indexing()))
    
    # Test 3: Index Status
    print("\n")
    results.append(("Index Status Check", test_index_status()))
    
    # Test 4: Bug Localization
    print("\n")
    results.append(("Bug Localization", test_java_bug_localization()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-language support is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")


if __name__ == "__main__":
    main()
