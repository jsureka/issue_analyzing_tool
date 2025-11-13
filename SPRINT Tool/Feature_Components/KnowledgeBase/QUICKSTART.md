# Knowledge Base System - Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide will help you set up and use the Knowledge Base System for bug localization.

---

## Prerequisites

✅ Python 3.8 or higher  
✅ Git installed  
✅ 8GB+ RAM recommended  
✅ GPU optional (speeds up indexing 5-10x)

---

## Step 1: Install Dependencies

```bash
cd "SPRINT Tool"
pip install -r requirements.txt
```

**Key packages installed:**

- `torch` - Deep learning
- `transformers` - Embedding models
- `faiss-cpu` - Vector search
- `tree-sitter` - Code parsing

---

## Step 2: Index Your First Repository

```python
from Feature_Components.knowledgeBase import IndexRepository

# Index a repository
result = IndexRepository(
    repo_path="/path/to/your/repository",
    repo_name="owner/repo"
)

print(f"✅ Indexed {result['total_functions']} functions")
print(f"✅ Generated {result['total_windows']} line windows")
print(f"⏱️  Time: {result['indexing_time_seconds']:.1f}s")
```

**What happens:**

1. Parses all Python files
2. Extracts functions and classes
3. Generates embeddings (768-dim vectors)
4. Creates line windows (48 tokens each)
5. Builds FAISS indices
6. Stores in `indices/` directory

**Expected time:**

- Small repo (100 files): ~1 minute
- Medium repo (1,000 files): ~5 minutes
- Large repo (5,000 files): ~15 minutes

---

## Step 3: Localize Your First Bug

```python
from Feature_Components.knowledgeBase import BugLocalization

# Localize a bug
results = BugLocalization(
    issue_title="Bug in data processing",
    issue_body="The process_data function crashes when input is empty",
    repo_owner="owner",
    repo_name="repo",
    repo_path="/path/to/your/repository",
    k=10  # Top 10 results
)

# Check results
print(f"Confidence: {results['confidence']}")
print(f"Top file: {results['top_files'][0]['file_path']}")
print(f"Top function: {results['top_files'][0]['functions'][0]['name']}")
```

**What you get:**

- Top 10 most relevant functions
- Line-level locations (if enabled)
- Confidence score (High/Medium/Low)
- Code snippets
- Similarity scores

---

## Step 4: Generate GitHub Comment

```python
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator

# Create comment generator
generator = CommentGenerator("owner", "repo")

# Generate markdown comment
comment = generator.generate_comment(
    results=results,
    confidence=results['confidence'],
    confidence_score=results['confidence_score']
)

print(comment)
```

**Output example:**

```markdown
## 🔍 Bug Localization Results

**Confidence:** High (92% probability) 🟢

### 🎯 Precise Line-Level Locations

#### 1. `process_data` in `src/module.py`

**⚠️ Lines 45-52** (Score: 0.89)
[View on GitHub](...)

\`\`\`python
def process_data(input: str) -> dict:
if not input: # ⚠️ Line 46
raise ValueError("Empty input")
return {}
\`\`\`
```

---

## Step 5: Monitor Performance

```python
from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger

# Get telemetry logger
telemetry = get_telemetry_logger()

# View statistics
stats = telemetry.get_statistics("24h")

print(f"Total requests: {stats['retrieval']['total_requests']}")
print(f"Success rate: {stats['retrieval']['success_rate']:.1%}")
print(f"Avg latency: {stats['retrieval']['avg_latency_ms']:.0f}ms")
```

---

## Common Use Cases

### Use Case 1: Integrate with SPRINT

The system is already integrated! When a new GitHub issue is created:

1. SPRINT receives webhook
2. Processes issue through Knowledge Base
3. Posts structured comment automatically
4. Applies confidence label
5. Logs telemetry

**No additional code needed!**

### Use Case 2: Batch Processing

Process multiple issues:

```python
issues = [
    {"title": "Bug 1", "body": "Description 1"},
    {"title": "Bug 2", "body": "Description 2"},
]

for issue in issues:
    results = BugLocalization(
        issue_title=issue["title"],
        issue_body=issue["body"],
        repo_owner="owner",
        repo_name="repo",
        repo_path="/path/to/repo"
    )
    print(f"{issue['title']}: {results['confidence']}")
```

### Use Case 3: Custom Confidence Thresholds

Calibrate confidence based on your validation data:

```python
from Feature_Components.KnowledgeBase.calibrator import ConfidenceCalibrator, ValidationResult

calibrator = ConfidenceCalibrator()

# Prepare validation results
validation_results = [
    ValidationResult(
        issue_id="1",
        predicted_functions=["func1", "func2", "func3"],
        true_function="func1",
        top_score=0.85,
        in_top_3=True
    ),
    # ... more results
]

# Compute calibration
calibration = calibrator.compute_calibration(validation_results)

# Save new thresholds
calibrator.save_calibration_config()
```

### Use Case 4: Historical Version Retrieval

Localize bugs in past commits:

```python
# Localize against specific commit
results = BugLocalization(
    issue_title="Bug in old version",
    issue_body="Issue description",
    repo_owner="owner",
    repo_name="repo",
    repo_path="/path/to/repo",
    commit_sha="abc123def456"  # Specific commit
)
```

---

## Configuration

### Basic Configuration

Edit `config.py`:

```python
# Model selection
DEFAULT_MODEL = "microsoft/unixcoder-base"

# Performance tuning
BATCH_SIZE_FUNCTIONS = 32  # Increase for faster indexing
BATCH_SIZE_WINDOWS = 64

# Retrieval settings
DEFAULT_TOP_K = 10  # Number of results
```

### Advanced Configuration

**Enable GPU acceleration:**

```python
# Automatic - no configuration needed
# System detects CUDA and uses GPU if available
```

**Adjust window size:**

```python
# In window_generator.py
window_size = 48  # Increase for more context
stride = 24  # Decrease for more overlap
```

**Customize confidence thresholds:**

```json
// calibration_config.json
{
  "thresholds": {
    "high": { "min_score": 0.8 }, // Stricter
    "medium": { "min_score": 0.6 },
    "low": { "max_score": 0.6 }
  }
}
```

---

## Troubleshooting

### Issue: "Repository not indexed"

**Solution:**

```python
IndexRepository(repo_path, repo_name)
```

### Issue: Slow indexing

**Solutions:**

1. Use GPU (automatic if available)
2. Reduce batch size if running out of memory
3. Index smaller repositories first

### Issue: Low confidence scores

**Solutions:**

1. Improve issue descriptions (more details)
2. Recalibrate thresholds with validation data
3. Check if repository is properly indexed

### Issue: Out of memory

**Solutions:**

```python
# Reduce batch sizes in config.py
BATCH_SIZE_FUNCTIONS = 16  # Default: 32
BATCH_SIZE_WINDOWS = 32  # Default: 64
```

---

## Next Steps

### Learn More

1. **Full Documentation**: See `README.md`
2. **API Reference**: Check function docstrings
3. **Examples**: See `tests/` directory
4. **Architecture**: Review design document

### Advanced Features

1. **Incremental Indexing**: Update indices on code changes
2. **Custom Models**: Use different embedding models
3. **Graph Features**: Leverage Neo4j code graph
4. **Batch Processing**: Process multiple issues efficiently

### Contribute

1. Add tests for new features
2. Update documentation
3. Submit pull requests
4. Report issues

---

## Quick Reference

### Essential Commands

```python
# Index repository
IndexRepository(repo_path, repo_name)

# Localize bug
BugLocalization(title, body, owner, name, path)

# Generate comment
CommentGenerator(owner, name).generate_comment(results, conf, score)

# Get statistics
get_telemetry_logger().get_statistics("24h")

# Apply label
AutoLabeler(token, owner, name).apply_confidence_label(issue_num, conf)
```

### File Locations

- **Indices**: `indices/`
- **Telemetry**: `telemetry_logs/`
- **Config**: `config.py`, `calibration_config.json`
- **Tests**: `tests/`

### Performance Targets

- ✅ Indexing: <15 min for 5,000 files
- ✅ Retrieval: <1s for function-level
- ✅ Line-level: <2s additional
- ✅ End-to-end: <10s total

---

## Support

**Need help?**

- 📖 Read full documentation: `README.md`
- 🐛 Report issues: GitHub Issues
- 📊 Check telemetry: `telemetry_logs/`
- 🧪 Run tests: `python -m unittest discover`

---

## Success! 🎉

You're now ready to use the Knowledge Base System for bug localization!

**What you can do:**

- ✅ Index repositories
- ✅ Localize bugs with high precision
- ✅ Generate structured GitHub comments
- ✅ Monitor performance
- ✅ Calibrate confidence
- ✅ Auto-label issues

**Happy bug hunting!** 🐛🔍
