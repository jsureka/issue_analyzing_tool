# Knowledge Base System - Testing Guide

## 🧪 Complete Testing Instructions

This guide will help you test all components of the Knowledge Base System.

---

## Quick Start

### 1. Run Quick Test (30 seconds)

```bash
cd "SPRINT Tool"
python quick_test.py
```

**What it tests:**

- ✅ All imports work
- ✅ Comment generator
- ✅ Confidence calibrator
- ✅ Telemetry logger

**Expected output:**

```
✅ All quick tests passed!
```

---

### 2. Run Component Tests (2 minutes)

```bash
cd "SPRINT Tool"
python test_knowledge_base_system.py
```

**What it tests:**

- ✅ Dependencies installed
- ✅ All components import correctly
- ✅ Comment generation with sample data
- ✅ Telemetry logging and statistics
- ✅ Confidence calibration
- ✅ Window generation
- ✅ Vector store operations

**Expected output:**

```
✅ All component tests passed!
```

---

### 3. Test with Real Repository (5-10 minutes)

```bash
cd "SPRINT Tool"
python test_with_real_repo.py
```

**What it does:**

1. Asks for repository path
2. Indexes the repository
3. Tests bug localization
4. Generates GitHub comment
5. Tests telemetry

**Example:**

```
Enter repository path: C:\path\to\your\repo
Enter repository name: owner/repo

✅ Indexing Complete!
   Files indexed: 50
   Functions found: 250
   Windows generated: 2500
   Time taken: 45.2s

✅ Bug localization tests passed!
✅ Comment saved to: sample_github_comment.md
```

---

## Unit Tests

### Run All Unit Tests

```bash
cd "SPRINT Tool/Feature_Components/KnowledgeBase/tests"
python -m unittest discover -s . -p "test_*.py"
```

### Run Specific Test File

```bash
# Test comment generator
python test_comment_generator.py

# Test telemetry
python test_telemetry.py

# Test Phase 2 integration
python test_phase2_integration.py
```

### Test Coverage

**36 Total Test Cases:**

- Comment Generator: 13 tests
- Telemetry Logger: 12 tests
- Phase 2 Integration: 11 tests

---

## Manual Testing

### Test 1: Index a Repository

```python
from Feature_Components.knowledgeBase import IndexRepository

result = IndexRepository(
    repo_path="C:/path/to/repo",
    repo_name="owner/repo"
)

print(f"Functions: {result['total_functions']}")
print(f"Windows: {result['total_windows']}")
```

**Expected:**

- Creates `indices/` directory
- Generates `.index` and `_metadata.json` files
- Completes in <15 minutes for 5,000 files

---

### Test 2: Bug Localization

```python
from Feature_Components.knowledgeBase import BugLocalization

results = BugLocalization(
    issue_title="Bug in data processing",
    issue_body="Function crashes on empty input",
    repo_owner="owner",
    repo_name="repo",
    repo_path="C:/path/to/repo",
    k=10
)

print(f"Confidence: {results['confidence']}")
print(f"Top file: {results['top_files'][0]['file_path']}")
```

**Expected:**

- Returns results in <10 seconds
- Includes confidence level
- Shows top functions and files

---

### Test 3: Comment Generation

```python
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator

gen = CommentGenerator("owner", "repo")
comment = gen.generate_comment(results, "high", 0.92)

print(comment)
```

**Expected:**

- Markdown-formatted comment
- Confidence badge with emoji
- GitHub permalinks
- Code snippets

---

### Test 4: Telemetry

```python
from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger

tel = get_telemetry_logger()
stats = tel.get_statistics("24h")

print(f"Requests: {stats['retrieval']['total_requests']}")
print(f"Success rate: {stats['retrieval']['success_rate']:.1%}")
print(f"Avg latency: {stats['retrieval']['avg_latency_ms']:.0f}ms")
```

**Expected:**

- Statistics computed correctly
- Logs written to `telemetry_logs/`
- JSON format

---

## Integration Testing

### Test SPRINT Integration

1. **Start SPRINT**:

   ```bash
   cd "SPRINT Tool"
   python main.py
   ```

2. **Create test issue** on GitHub

3. **Check results**:
   - Comment posted automatically
   - Confidence label applied
   - Telemetry logged

---

## Performance Testing

### Test Indexing Performance

```python
import time
from Feature_Components.knowledgeBase import IndexRepository

start = time.time()
result = IndexRepository(repo_path, repo_name)
duration = time.time() - start

print(f"Time: {duration:.1f}s")
print(f"Files/sec: {result['total_files'] / duration:.1f}")
```

**Targets:**

- Small repo (100 files): <1 minute
- Medium repo (1,000 files): <5 minutes
- Large repo (5,000 files): <15 minutes

---

### Test Retrieval Performance

```python
import time
from Feature_Components.knowledgeBase import BugLocalization

start = time.time()
results = BugLocalization(title, body, owner, name, path)
duration = time.time() - start

print(f"Latency: {duration:.2f}s")
```

**Targets:**

- Function-level: <1 second
- Line-level: <3 seconds total
- End-to-end: <10 seconds

---

## Troubleshooting Tests

### Issue: Import Errors

**Problem:**

```
ModuleNotFoundError: No module named 'torch'
```

**Solution:**

```bash
pip install torch transformers numpy faiss-cpu
```

---

### Issue: Index Not Found

**Problem:**

```
Repository not indexed
```

**Solution:**

```python
# Reindex the repository
IndexRepository(repo_path, repo_name)
```

---

### Issue: Slow Performance

**Problem:** Tests taking too long

**Solutions:**

1. Use GPU (automatic if available)
2. Reduce batch sizes in `config.py`
3. Test with smaller repository first

---

### Issue: Memory Errors

**Problem:**

```
RuntimeError: CUDA out of memory
```

**Solutions:**

```python
# In config.py, reduce batch sizes
BATCH_SIZE_FUNCTIONS = 16  # Default: 32
BATCH_SIZE_WINDOWS = 32  # Default: 64
```

---

## Test Checklist

Before deploying to production, verify:

### Core Functionality

- [ ] Repository indexing works
- [ ] Bug localization returns results
- [ ] Confidence calibration works
- [ ] Comment generation works
- [ ] Telemetry logging works

### Performance

- [ ] Indexing completes in reasonable time
- [ ] Retrieval latency <10 seconds
- [ ] Memory usage acceptable
- [ ] No memory leaks

### Integration

- [ ] SPRINT integration works
- [ ] GitHub comments post correctly
- [ ] Labels applied correctly
- [ ] No conflicts with other features

### Error Handling

- [ ] Handles missing repositories
- [ ] Handles empty results
- [ ] Handles network errors
- [ ] Logs errors appropriately

---

## Continuous Testing

### Daily Tests

Run quick test daily:

```bash
python quick_test.py
```

### Weekly Tests

Run full component tests weekly:

```bash
python test_knowledge_base_system.py
```

### Monthly Tests

Test with real repositories monthly:

```bash
python test_with_real_repo.py
```

---

## Test Results

### Expected Test Results

**Quick Test:**

```
✅ All quick tests passed!
Time: ~30 seconds
```

**Component Test:**

```
✅ All component tests passed!
Time: ~2 minutes
```

**Real Repository Test:**

```
✅ All tests completed successfully!
Time: ~5-10 minutes (depends on repo size)
```

---

## Reporting Issues

If tests fail:

1. **Check logs**:

   - Console output
   - `telemetry_logs/`
   - Error messages

2. **Gather information**:

   - Python version
   - Dependency versions
   - Repository size
   - Error traceback

3. **Try fixes**:

   - Reinstall dependencies
   - Clear indices
   - Reindex repository
   - Check disk space

4. **Report**:
   - Include error message
   - Include steps to reproduce
   - Include system information

---

## Success Criteria

Tests are successful when:

✅ All imports work  
✅ All component tests pass  
✅ Repository indexes successfully  
✅ Bug localization returns results  
✅ Comments generate correctly  
✅ Telemetry logs properly  
✅ Performance meets targets  
✅ No memory leaks  
✅ Error handling works

---

## Next Steps

After successful testing:

1. ✅ Deploy to production
2. ✅ Monitor telemetry
3. ✅ Collect user feedback
4. ✅ Optimize performance
5. ✅ Add more tests as needed

---

## Support

For testing help:

- 📖 See README.md for documentation
- 🚀 See QUICKSTART.md for examples
- 📊 Check telemetry logs
- 🐛 Report issues on GitHub

---

**Happy Testing!** 🧪✅
