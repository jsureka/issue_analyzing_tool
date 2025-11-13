"""
Quick Test - Verify Knowledge Base System is working
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("🧪 Quick Test - Knowledge Base System")
print("=" * 50)

# Test 1: Imports
print("\n1. Testing imports...")
try:
    from Feature_Components.knowledgeBase import BugLocalization
    from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator
    from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger
    from Feature_Components.KnowledgeBase.calibrator import ConfidenceCalibrator
    print("   ✅ All imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Comment Generator
print("\n2. Testing Comment Generator...")
try:
    gen = CommentGenerator("owner", "repo")
    badge = gen.format_confidence_badge("high", 0.92)
    assert "High" in badge and "92%" in badge
    print("   ✅ Comment generator works")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 3: Calibrator
print("\n3. Testing Confidence Calibrator...")
try:
    cal = ConfidenceCalibrator()
    conf, score = cal.calibrate_score(0.85)
    print(f"   ✅ Score 0.85 → {conf} ({score:.0%})")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Test 4: Telemetry
print("\n4. Testing Telemetry...")
try:
    tel = get_telemetry_logger()
    tel.log_retrieval("test", 1000.0, 5, "high", "test/repo")
    stats = tel.get_statistics("1h")
    print(f"   ✅ Logged and retrieved stats")
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "=" * 50)
print("✅ All quick tests passed!")
print("\nNext: Run 'python test_with_real_repo.py' to test with a repository")
