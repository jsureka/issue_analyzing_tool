# Knowledge Base System - Complete Documentation

## Overview

The Knowledge Base System is a sophisticated bug localization platform that enhances SPRINT's capabilities through five progressive phases. It provides function-level and line-level bug localization with calibrated confidence scores, automatic GitHub integration, and comprehensive performance monitoring.

## Table of Contents

1. [Architecture](#architecture)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [API Reference](#api-reference)
6. [Phase Details](#phase-details)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Performance](#performance)
10. [Troubleshooting](#troubleshooting)

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Webhook                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              SPRINT Event Handler                            │
│  - processIssueEvents.py                                     │
│  - Duplicate Detection                                       │
│  - Severity Prediction                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Knowledge Base System (Main API)                   │
│  - BugLocalization()                                         │
│  - IndexRepository()                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│  Issue Processor │    │  Dense Retriever │
│  - Text cleaning │    │  - FAISS search  │
│  - Embedding     │    │  - Top-K results │
└──────────────────┘    └────────┬─────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
          ┌──────────────────┐    ┌──────────────────┐
          │  Line Reranker   │    │   Calibrator     │
          │  - Window search │    │  - Confidence    │
          │  - Best lines    │    │  - Thresholds    │
          └──────────────────┘    └────────┬─────────┘
                                           │
                              ┌────────────┴────────────┐
                              ▼                         ▼
                    ┌──────────────────┐    ┌──────────────────┐
                    │ Comment Generator│    │   Auto Labeler   │
                    │ - Markdown format│    │  - GitHub labels │
                    │ - Permalinks     │    │  - Confidence    │
                    └──────────────────┘    └──────────────────┘
```

### Data Flow

1. **Indexing Phase**:

   ```
   Repository → Parser → Functions → Embedder → FAISS Index
                    ↓
                  Windows → Embedder → Window Index
                    ↓
              Graph Store (Neo4j)
   ```

2. **Retrieval Phase**:
   ```
   Issue → Processor → Embedding
                ↓
          Dense Retriever → Top Functions
                ↓
          Line Reranker → Best Windows
                ↓
          Calibrator → Confidence
                ↓
          Formatter → Results
   ```

---

## Features

### Phase 1: Foundation

- ✅ Multi-language code parsing with tree-sitter (Python, Java)
- ✅ Function-level embeddings (UniXcoder/GraphCodeBERT)
- ✅ FAISS vector store for similarity search
- ✅ Neo4j code knowledge graph
- ✅ Dense retrieval with top-K results
- ✅ Language-agnostic architecture

### Phase 2: SPRINT Integration

- ✅ Structured GitHub comments with markdown
- ✅ Confidence badges (🟢 High, 🟡 Medium, 🔴 Low)
- ✅ GitHub permalinks to code
- ✅ Real-time telemetry logging
- ✅ Performance monitoring (<10s latency)
- ✅ Backward compatibility

### Phase 3: Line-Level Localization

- ✅ Overlapping line windows (48 tokens, 24 stride)
- ✅ Window embeddings and FAISS index
- ✅ Two-stage retrieval (functions → windows)
- ✅ Line-level highlights in comments (⚠️)
- ✅ Context-aware code snippets

### Phase 4: Confidence Calibration

- ✅ Calibration curve from validation data
- ✅ Score-to-confidence mapping
- ✅ Automatic GitHub labeling
- ✅ High/Medium/Low confidence levels
- ✅ Precision@3 targets (90%/70%/40%)

### Phase 5: Incremental Indexing

- ✅ Git diff-based change detection
- ✅ File classification (added/modified/deleted)
- ✅ Index registry for version management
- ✅ Storage statistics and monitoring
- ⚙️ Incremental update framework (foundation)

---

## Installation

### Prerequisites

```bash
# Python 3.8+
python --version

# Git
git --version

# Neo4j (optional, for graph features)
# Download from: https://neo4j.com/download/
```

### Dependencies

```bash
cd "SPRINT Tool"
pip install -r requirements.txt
```

Required packages:

- `torch` - PyTorch for deep learning
- `transformers` - Hugging Face models
- `faiss-cpu` - Vector similarity search
- `tree-sitter` - Code parsing
- `tree-sitter-python` - Python grammar
- `neo4j` - Graph database driver
- `requests` - HTTP client
- `numpy` - Numerical computing

---

## Quick Start

### 1. Index a Repository

```python
from Feature_Components.knowledgeBase import IndexRepository

# Index a repository
result = IndexRepository(
    repo_path="/path/to/repository",
    repo_name="owner/repo",
    model_name="microsoft/unixcoder-base",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)

print(f"Indexed {result['total_functions']} functions")
print(f"Generated {result['total_windows']} line windows")
```

### 2. Localize a Bug

```python
from Feature_Components.knowledgeBase import BugLocalization

# Localize bug from issue
results = BugLocalization(
    issue_title="Bug in data processing",
    issue_body="The process_data function crashes when input is empty",
    repo_owner="owner",
    repo_name="repo",
    repo_path="/path/to/repository",
    k=10,  # Top 10 results
    enable_line_level=True  # Enable line-level localization
)

# Results include:
# - top_files: Function-level results
# - line_level_results: Line-level results (if enabled)
# - confidence: Overall confidence level
# - confidence_score: Calibrated probability
```

### 3. Generate GitHub Comment

```python
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator

generator = CommentGenerator("owner", "repo")

comment = generator.generate_comment(
    results=results,
    confidence=results['confidence'],
    confidence_score=results['confidence_score']
)

print(comment)  # Markdown-formatted comment
```

---

## API Reference

### Main API Functions

#### `BugLocalization()`

Performs bug localization on a GitHub issue.

**Parameters:**

- `issue_title` (str): GitHub issue title
- `issue_body` (str): GitHub issue body text
- `repo_owner` (str): Repository owner
- `repo_name` (str): Repository name
- `repo_path` (str): Local path to cloned repository
- `commit_sha` (str, optional): Specific commit to localize against
- `k` (int, default=10): Number of top results to return
- `enable_line_level` (bool, default=True): Enable line-level localization

**Returns:**

```python
{
    'repository': 'owner/repo',
    'commit_sha': 'abc123...',
    'timestamp': '2025-11-13T12:00:00Z',
    'total_results': 10,
    'confidence': 'high',
    'confidence_score': 0.92,
    'top_files': [
        {
            'file_path': 'src/module.py',
            'score': 0.87,
            'functions': [...]
        }
    ],
    'line_level_results': [  # If enabled
        {
            'function_name': 'process_data',
            'file_path': 'src/module.py',
            'line_start': 45,
            'line_end': 52,
            'snippet': '...',
            'score': 0.89
        }
    ]
}
```

#### `IndexRepository()`

Indexes a repository for bug localization.

**Parameters:**

- `repo_path` (str): Path to repository root
- `repo_name` (str): Repository name (e.g., "owner/repo")
- `model_name` (str, default="microsoft/unixcoder-base"): Embedding model
- `neo4j_uri` (str): Neo4j connection URI
- `neo4j_user` (str): Neo4j username
- `neo4j_password` (str): Neo4j password

**Returns:**

```python
{
    'success': True,
    'repo_name': 'owner/repo',
    'commit_sha': 'abc123...',
    'total_files': 100,
    'total_functions': 500,
    'total_windows': 5000,
    'indexing_time_seconds': 120.5
}
```

### Component APIs

#### CommentGenerator

```python
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator

generator = CommentGenerator(repo_owner="owner", repo_name="repo")

# Generate comment
comment = generator.generate_comment(results, confidence, confidence_score)

# Format confidence badge
badge = generator.format_confidence_badge("high", 0.92)
```

#### TelemetryLogger

```python
from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger

telemetry = get_telemetry_logger()

# Log retrieval
telemetry.log_retrieval(
    issue_id="123",
    latency_ms=1500.0,
    top_k=10,
    confidence="high",
    repo_name="owner/repo"
)

# Get statistics
stats = telemetry.get_statistics("24h")
print(f"Success rate: {stats['retrieval']['success_rate']:.2%}")
print(f"Avg latency: {stats['retrieval']['avg_latency_ms']:.0f}ms")
```

#### AutoLabeler

```python
from Feature_Components.KnowledgeBase.auto_labeler import AutoLabeler

labeler = AutoLabeler(github_token, "owner", "repo")

# Ensure labels exist
labeler.ensure_labels_exist()

# Apply confidence label
labeler.apply_confidence_label(issue_number=123, confidence="high")
```

---

## Phase Details

### Phase 1: Foundation (Complete)

**Purpose**: Build core indexing and retrieval infrastructure

**Components**:

- `parser.py` - Tree-sitter Python parser
- `embedder.py` - Code embedding generation
- `vector_store.py` - FAISS similarity search
- `graph_store.py` - Neo4j code graph
- `retriever.py` - Dense retrieval
- `indexer.py` - Repository indexing orchestration

**Usage**:

```python
# Index repository
from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer

indexer = RepositoryIndexer(
    model_name="microsoft/unixcoder-base",
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)

result = indexer.index_repository("/path/to/repo", "owner/repo")
```

### Phase 2: SPRINT Integration (Complete)

**Purpose**: Integrate with SPRINT's GitHub app workflow

**Components**:

- `comment_generator.py` - GitHub comment formatting
- `telemetry.py` - Performance monitoring
- Updated `processIssueEvents.py` - Event handling
- Updated `createCommentBugLocalization.py` - Comment posting

**Features**:

- Structured markdown comments
- Confidence badges with emojis
- GitHub permalinks
- Real-time telemetry
- <10s end-to-end latency

**Example Comment**:

```markdown
## 🔍 Bug Localization Results

**Confidence:** High (92% probability) 🟢

### Top Candidate Functions

#### 1. `process_data` in `src/module.py` (Score: 0.87)

**Lines 45-78** | [View on GitHub](...)

\`\`\`python
def process_data(input: str) -> dict:
result = {}
return result
\`\`\`
```

### Phase 3: Line-Level Localization (Complete)

**Purpose**: Provide fine-grained line-level bug localization

**Components**:

- `window_generator.py` - Line window extraction
- `line_reranker.py` - Two-stage retrieval
- Extended `vector_store.py` - Window FAISS index
- Extended `embedder.py` - Window embeddings

**Algorithm**:

1. Generate overlapping 48-token windows with 24-token stride
2. Embed all windows using same model as functions
3. Store in separate FAISS index
4. Two-stage retrieval:
   - Stage 1: Retrieve top-10 functions
   - Stage 2: Rerank windows within those functions
5. Return best line range per function

**Configuration**:

```python
# In window_generator.py
window_size = 48  # tokens
stride = 24  # 50% overlap
```

### Phase 4: Confidence Calibration (Complete)

**Purpose**: Quantify and expose reliability of predictions

**Components**:

- `calibrator.py` - Confidence calibration
- `auto_labeler.py` - GitHub label management

**Calibration Process**:

1. Collect validation dataset with ground truth
2. Run retrieval and record scores
3. Compute precision@3 for different thresholds
4. Find thresholds where:
   - High: precision@3 ≥ 90%
   - Medium: precision@3 ≥ 70%
   - Low: precision@3 < 70%
5. Save thresholds to configuration

**Labels Created**:

- `bug-localization:high-confidence` (🟢 Green)
- `bug-localization:medium-confidence` (🟡 Yellow)
- `bug-localization:low-confidence` (🔴 Red)

### Phase 5: Incremental Indexing (Foundation Complete)

**Purpose**: Handle new commits and historical versions

**Components**:

- `incremental_indexer.py` - Git diff analysis
- `index_registry.py` - Version management

**Features**:

- Git diff-based change detection
- File classification (added/modified/deleted)
- Fallback to full reindex for large changes (>50 files)
- Index registry for tracking versions
- Storage statistics

**Usage**:

```python
from Feature_Components.KnowledgeBase.incremental_indexer import IncrementalIndexer

indexer = IncrementalIndexer("/path/to/repo")

# Get changed files
added, modified, deleted = indexer.get_changed_files(
    old_commit="abc123",
    new_commit="def456"
)

# Update index
result = indexer.update_index("abc123", "def456")
```

---

## Multi-Language Support

### Supported Languages

The Knowledge Base System supports multiple programming languages:

| Language | Extensions | Parser             | Status             |
| -------- | ---------- | ------------------ | ------------------ |
| Python   | `.py`      | tree-sitter-python | ✅ Fully Supported |
| Java     | `.java`    | tree-sitter-java   | ✅ Fully Supported |

### Language Detection

The system automatically detects the programming language based on file extension:

```python
from Feature_Components.KnowledgeBase.parser_factory import ParserFactory, LanguageDetector

factory = ParserFactory()
detector = LanguageDetector(factory)

# Detect language
language = detector.detect_language("Example.java")  # Returns "java"
language = detector.detect_language("example.py")    # Returns "python"

# Check if supported
is_supported = detector.is_supported("example.js")   # Returns False
```

### Mixed-Language Repositories

The system seamlessly handles repositories containing multiple programming languages:

```python
# Index a repository with both Python and Java files
result = IndexRepository(
    repo_path="/path/to/mixed-repo",
    repo_name="owner/mixed-repo"
)

# Results include language statistics
print(result['languages'])  # {'python': 150, 'java': 200}
```

### Language-Specific Features

#### Syntax Highlighting

GitHub comments automatically use language-specific syntax highlighting:

````markdown
#### 1. `processData` in `Processor.java`

```java
public Map<String, Object> processData(String input) {
    Map<String, Object> result = new HashMap<>();
    return result;
}
```
````

#### Java-Specific Parsing

The Java parser extracts:

- Methods from classes, interfaces, and enums
- Javadoc comments as docstrings
- Method signatures with modifiers and types
- Import statements
- Method invocation relationships

Example:

```java
/**
 * Process input data and return result
 * @param input The input string
 * @return Processed result map
 */
public Map<String, Object> processData(String input) {
    // Method body
}
```

### Adding New Languages

To add support for a new language:

1. **Install tree-sitter grammar**:

   ```bash
   pip install tree-sitter-javascript
   ```

2. **Create parser class**:

   ```python
   from Feature_Components.KnowledgeBase.language_parser import LanguageParser

   class JavaScriptParser(LanguageParser):
       def __init__(self):
           self.language = Language(tsjavascript.language(), "javascript")
           # Implement abstract methods
   ```

3. **Register in ParserFactory**:

   ```python
   # In parser_factory.py
   self.register_parser("javascript", JavaScriptParser, [".js", ".jsx"])
   ```

4. **Update configuration**:

   ```python
   # In config.py
   SUPPORTED_LANGUAGES['javascript'] = {
       'extensions': ['.js', '.jsx'],
       'parser': 'JavaScriptParser',
       'syntax_highlight': 'javascript'
   }
   ```

5. **Add tests** and documentation

---

## Configuration

### Model Configuration

Edit `config.py`:

```python
# Embedding model
DEFAULT_MODEL = "microsoft/unixcoder-base"
# Alternatives: "microsoft/graphcodebert-base"

# Window settings
WINDOW_SIZE = 48  # tokens
WINDOW_STRIDE = 24  # tokens

# Retrieval settings
DEFAULT_TOP_K = 10
MAX_TOP_K = 50

# Performance settings
BATCH_SIZE_FUNCTIONS = 32
BATCH_SIZE_WINDOWS = 64
```

### Neo4j Configuration

```python
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
```

### Index Storage

```python
INDEX_DIR = "indices"  # Directory for FAISS indices
TELEMETRY_DIR = "telemetry_logs"  # Directory for logs
```

### Calibration Configuration

Edit `calibration_config.json`:

```json
{
  "model_version": "unixcoder-base",
  "thresholds": {
    "high": {
      "min_score": 0.75,
      "precision_at_3": 0.9
    },
    "medium": {
      "min_score": 0.55,
      "max_score": 0.75,
      "precision_at_3": 0.7
    },
    "low": {
      "max_score": 0.55,
      "precision_at_3": 0.4
    }
  }
}
```

---

## Testing

### Run All Tests

```bash
cd "SPRINT Tool/Feature_Components/KnowledgeBase/tests"

# Run with unittest
python -m unittest discover -s . -p "test_*.py"

# Or run individual test files
python test_comment_generator.py
python test_telemetry.py
python test_phase2_integration.py
```

### Test Coverage

- **Comment Generator**: 13 tests
- **Telemetry Logger**: 12 tests
- **Phase 2 Integration**: 11 tests
- **Total**: 36 comprehensive test cases

### Example Test

```python
import unittest
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator

class TestCommentGenerator(unittest.TestCase):
    def test_confidence_badge_high(self):
        generator = CommentGenerator("owner", "repo")
        badge = generator.format_confidence_badge("high", 0.92)

        self.assertIn("High", badge)
        self.assertIn("92%", badge)
        self.assertIn("🟢", badge)
```

---

## Performance

### Benchmarks

**Indexing Performance**:

- 5,000 Python files: ~15 minutes
- 500 functions: ~30 seconds
- 5,000 line windows: ~2 minutes additional

**Retrieval Performance**:

- Function-level search: <1 second
- Line-level reranking: <2 seconds additional
- End-to-end (issue → comment): <10 seconds

**Storage Requirements**:

- Function embeddings: ~4KB per function
- Window embeddings: ~4KB per window
- Metadata: ~500 bytes per function
- Example: 5,000 functions + 50,000 windows = ~250MB

### Optimization Tips

1. **Use GPU for indexing**:

   ```python
   # Embedder automatically detects CUDA
   # Speeds up indexing by 5-10x
   ```

2. **Batch processing**:

   ```python
   # Already optimized in code
   BATCH_SIZE_FUNCTIONS = 32
   BATCH_SIZE_WINDOWS = 64
   ```

3. **Index caching**:

   ```python
   # Indices loaded once and cached in memory
   # Subsequent queries are fast
   ```

4. **Incremental updates**:
   ```python
   # Use incremental indexing for small changes
   # Fallback to full reindex for >50 files
   ```

---

## Troubleshooting

### Common Issues

#### 1. "Repository not indexed"

**Problem**: Trying to localize bug in unindexed repository

**Solution**:

```python
from Feature_Components.knowledgeBase import IndexRepository

IndexRepository(
    repo_path="/path/to/repo",
    repo_name="owner/repo"
)
```

#### 2. "Model loading failed"

**Problem**: Embedding model not found or download failed

**Solution**:

```bash
# Manually download model
python -c "from transformers import AutoModel; AutoModel.from_pretrained('microsoft/unixcoder-base')"
```

#### 3. "Neo4j connection failed"

**Problem**: Cannot connect to Neo4j database

**Solution**:

```bash
# Start Neo4j
neo4j start

# Or skip graph features (optional)
# System works without Neo4j, just no graph-based features
```

#### 4. "FAISS index not found"

**Problem**: Index files missing or corrupted

**Solution**:

```python
# Reindex repository
IndexRepository(repo_path, repo_name)
```

#### 5. "Latency exceeds 10 seconds"

**Problem**: Slow retrieval performance

**Solutions**:

- Check if index is loaded in memory
- Reduce `k` parameter (fewer results)
- Disable line-level localization temporarily
- Check system resources (CPU/RAM)

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Telemetry Analysis

Check performance metrics:

```python
from Feature_Components.KnowledgeBase.telemetry import get_telemetry_logger

telemetry = get_telemetry_logger()
stats = telemetry.get_statistics("24h")

print(f"Total requests: {stats['retrieval']['total_requests']}")
print(f"Success rate: {stats['retrieval']['success_rate']:.2%}")
print(f"Avg latency: {stats['retrieval']['avg_latency_ms']:.0f}ms")
print(f"P95 latency: {stats['retrieval']['p95_latency_ms']:.0f}ms")
```

---

## Contributing

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all functions
- Include logging statements

### Adding New Features

1. Create feature branch
2. Implement feature with tests
3. Update documentation
4. Submit pull request

### Testing Requirements

- All new code must have tests
- Maintain >80% code coverage
- All tests must pass

---

## License

[Your License Here]

---

## Support

For issues and questions:

- GitHub Issues: [repository]/issues
- Documentation: This README
- Telemetry logs: Check `telemetry_logs/` directory

---

## Changelog

### Version 1.0.0 (Current)

- ✅ Phase 1: Foundation complete
- ✅ Phase 2: SPRINT Integration complete
- ✅ Phase 3: Line-Level Localization complete
- ✅ Phase 4: Confidence Calibration complete
- ✅ Phase 5: Incremental Indexing foundation complete

### Version 1.1.0 (Multi-Language Support)

- ✅ Java language support added
- ✅ Language-agnostic parser architecture
- ✅ ParserFactory for automatic language detection
- ✅ Language-specific syntax highlighting in comments
- ✅ Mixed-language repository support

### Upcoming

- Full incremental update implementation
- Additional language support (JavaScript, TypeScript, C++)
- Advanced graph-based retrieval
- Fix generation capabilities
