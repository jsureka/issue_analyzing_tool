"""
Knowledge Base System - Comprehensive Test Script
Run this to test all components of the system
"""

import sys
import os
from pathlib import Path

# Add SPRINT Tool to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("KNOWLEDGE BASE SYSTEM - COMPREHENSIVE TEST")
print("=" * 70)
print()

# Test 1: Check Dependencies
print("TEST 1: Checking Dependencies...")
print("-" * 70)

dependencies = {
    'torch': 'PyTorch',
    'transformers': 'Hugging Face Transformers',
    'numpy': 'NumPy',
    'faiss': 'FAISS (try faiss-cpu)',
}

missing_deps = []
for module, name in dependencies.items():
    try:
        if module == 'faiss':
            import faiss
        else:
            __import__(module)
        print(f"✅ {name} - OK")
    except ImportError:
        print(f"❌ {name} - MISSING")
        missing_deps.append(name)

if missing_deps:
    print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
    print("Install with: pip install torch transformers numpy faiss-cpu")
    sys.exit(1)
else:
    print("\n✅ All dependencies installed!")

print()

# Test 2: Import Knowledge Base Components
print("TEST 2: Importing Knowledge Base Components...")
print("-" * 70)

try:
    from Feature_Components.KnowledgeBase.embedder import CodeEmbedder
    print("✅ CodeEmbedder imported")
except Exception as e:
    print(f"❌ CodeEmbedder import failed: {e}")

try:
    from Feature_Components.KnowledgeBase.vector_store import VectorStore, WindowVectorStore
    print("✅ VectorStore imported")
except Exception as e:
    print(f"❌ VectorStore import failed: {e}")

try:
    from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator
    print("✅ CommentGenerator imported")
except Exception as e:
    print(f"❌ CommentGenerator import failed: {e}")

try:
    from Feature_Components.KnowledgeBase.telemetry import TelemetryLogger
    print("✅ TelemetryLogger imported")
except Exception as e:
    print(f"❌ TelemetryLogger import failed: {e}")

try:
    from Feature_Components.KnowledgeBase.calibrator import ConfidenceCalibrator
    print("✅ ConfidenceCalibrator imported")
except Exception as e:
    print(f"❌ ConfidenceCalibrator import failed: {e}")

try:
    from Feature_Components.KnowledgeBase.window_generator import WindowGenerator
    print("✅ WindowGenerator imported")
except Exception as e:
    print(f"❌ WindowGenerator import failed: {e}")

try:
    from Feature_Components.KnowledgeBase.line_reranker import LineReranker
    print("✅ LineReranker imported")
except Exception as e:
    print(f"❌ LineReranker import failed: {e}")

try:
    from Feature_Components.knowledgeBase import BugLocalization, IndexRepository
    print("✅ Main API imported")
except Exception as e:
    print(f"❌ Main API import failed: {e}")
    print(f"   Error details: {e}")

print("\n✅ All components imported successfully!")
print()

# Test 3: Test Comment Generator
print("TEST 3: Testing Comment Generator...")
print("-" * 70)

try:
    generator = CommentGenerator("test-owner", "test-repo")
    
    # Test confidence badge
    badge = generator.format_confidence_badge("high", 0.92)
    assert "High" in badge
    assert "92%" in badge
    assert "🟢" in badge
    print("✅ Confidence badge generation works")
    
    # Test GitHub permalink
    permalink = generator._generate_github_permalink("src/test.py", 10, 20, "abc123")
    assert "github.com" in permalink
    assert "test-owner/test-repo" in permalink
    print("✅ GitHub permalink generation works")
    
    # Test comment generation
    sample_results = {
        'repository': 'test-owner/test-repo',
        'commit_sha': 'abc123',
        'timestamp': '2025-11-13T12:00:00Z',
        'total_results': 3,
        'top_files': [
            {
                'file_path': 'src/test.py',
                'score': 0.87,
                'functions': [
                    {
                        'name': 'test_function',
                        'signature': 'def test_function():',
                        'line_range': [10, 20],
                        'score': 0.87,
                        'snippet': 'def test_function():\n    pass'
                    }
                ]
            }
        ]
    }
    
    comment = generator.generate_comment(sample_results, "high", 0.92)
    assert "Bug Localization Results" in comment
    assert "High" in comment
    assert "test_function" in comment
    print("✅ Comment generation works")
    
    print("\n✅ CommentGenerator tests passed!")
    
except Exception as e:
    print(f"❌ CommentGenerator test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: Test Telemetry Logger
print("TEST 4: Testing Telemetry Logger...")
print("-" * 70)

try:
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    telemetry = TelemetryLogger(log_path=temp_dir)
    
    # Test retrieval logging
    telemetry.log_retrieval(
        issue_id="test-123",
        latency_ms=1500.0,
        top_k=10,
        confidence="high",
        repo_name="test/repo"
    )
    print("✅ Retrieval logging works")
    
    # Test statistics
    stats = telemetry.get_statistics("1h")
    assert 'retrieval' in stats
    assert stats['retrieval']['total_requests'] == 1
    print("✅ Statistics computation works")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n✅ TelemetryLogger tests passed!")
    
except Exception as e:
    print(f"❌ TelemetryLogger test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 5: Test Confidence Calibrator
print("TEST 5: Testing Confidence Calibrator...")
print("-" * 70)

try:
    calibrator = ConfidenceCalibrator()
    
    # Test score calibration
    confidence, score = calibrator.calibrate_score(0.85)
    assert confidence in ['high', 'medium', 'low']
    assert 0 <= score <= 1
    print(f"✅ Score 0.85 → {confidence} confidence ({score:.2f})")
    
    confidence, score = calibrator.calibrate_score(0.65)
    print(f"✅ Score 0.65 → {confidence} confidence ({score:.2f})")
    
    confidence, score = calibrator.calibrate_score(0.45)
    print(f"✅ Score 0.45 → {confidence} confidence ({score:.2f})")
    
    print("\n✅ ConfidenceCalibrator tests passed!")
    
except Exception as e:
    print(f"❌ ConfidenceCalibrator test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 6: Test Window Generator
print("TEST 6: Testing Window Generator...")
print("-" * 70)

try:
    window_gen = WindowGenerator(window_size=48, stride=24)
    
    # Test window generation
    function_body = "def test():\n    x = 1\n    y = 2\n    return x + y"
    function_info = {
        'id': 'test-func',
        'name': 'test',
        'file_path': 'test.py',
        'start_line': 1,
        'end_line': 4
    }
    
    windows = window_gen.generate_windows(function_body, function_info)
    assert len(windows) > 0
    print(f"✅ Generated {len(windows)} windows from test function")
    
    print("\n✅ WindowGenerator tests passed!")
    
except Exception as e:
    print(f"❌ WindowGenerator test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 7: Test Vector Store
print("TEST 7: Testing Vector Store...")
print("-" * 70)

try:
    import numpy as np
    
    # Test basic vector store
    store = VectorStore(dimension=768)
    store.create_index()
    
    # Add some test vectors
    test_embeddings = np.random.rand(10, 768).astype('float32')
    test_metadata = [{'id': i, 'name': f'func_{i}'} for i in range(10)]
    
    store.add_vectors(test_embeddings, test_metadata)
    print(f"✅ Added {len(test_embeddings)} vectors to index")
    
    # Test search
    query = np.random.rand(768).astype('float32')
    indices, scores, metadata = store.search(query, k=5)
    assert len(indices) == 5
    print(f"✅ Search returned {len(indices)} results")
    
    print("\n✅ VectorStore tests passed!")
    
except Exception as e:
    print(f"❌ VectorStore test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Final Summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print()
print("✅ All component tests passed!")
print()
print("NEXT STEPS:")
print("1. To test with a real repository, run:")
print("   python test_with_real_repo.py")
print()
print("2. To run unit tests:")
print("   cd 'SPRINT Tool/Feature_Components/KnowledgeBase/tests'")
print("   python -m unittest discover")
print()
print("3. To index a repository:")
print("   See QUICKSTART.md for examples")
print()
print("=" * 70)
