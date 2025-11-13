# Knowledge Base System Tests

This directory contains comprehensive tests for the Knowledge Base System.

## Test Structure

- `test_parser.py` - Unit tests for Python code parser
- `test_embedder.py` - Unit tests for embedding generation
- `test_vector_store.py` - Unit tests for FAISS vector store
- `test_integration.py` - Integration tests for end-to-end workflows
- `test_performance.py` - Performance benchmarks
- `run_tests.py` - Test runner script

## Running Tests

### Run All Tests

```bash
cd "SPRINT Tool/Feature_Components/KnowledgeBase/tests"
python run_tests.py all
```

### Run Specific Test Suites

```bash
# Unit tests only (fast, no external dependencies)
python run_tests.py unit

# Integration tests (requires Neo4j)
python run_tests.py integration

# Performance benchmarks
python run_tests.py performance
```

### Run Individual Test Files

```bash
# Parser tests
python test_parser.py

# Embedder tests (requires model download)
python test_embedder.py

# Vector store tests
python test_vector_store.py

# Integration tests
python test_integration.py

# Performance tests
python test_performance.py
```

## Test Requirements

### Unit Tests

- No external dependencies
- Fast execution (< 1 minute)
- Test individual components in isolation

### Integration Tests

- Requires Neo4j running on `bolt://localhost:7687`
- Default credentials: `neo4j/password`
- Tests complete workflows

### Performance Tests

- Benchmarks parsing, embedding, search, and indexing
- Requires embedding model download (first run)
- Provides performance metrics

## Prerequisites

### For All Tests

```bash
pip install -r requirements.txt
```

### For Integration Tests

1. Install Neo4j:

   - Download from https://neo4j.com/download/
   - Or use Docker: `docker run -p 7687:7687 -p 7474:7474 neo4j`

2. Set password to "password" or update test configuration

### For Embedder Tests

- First run will download UniXcoder model (~500MB)
- Requires internet connection
- Model is cached for subsequent runs

## Test Coverage

### Parser Tests

- ✓ Simple function extraction
- ✓ Class and method extraction
- ✓ Import statement extraction
- ✓ Function call extraction
- ✓ Nested functions
- ✓ Line number accuracy
- ✓ Error handling for malformed code

### Embedder Tests

- ✓ Model loading and caching
- ✓ Single function embedding
- ✓ Batch embedding generation
- ✓ Issue text embedding
- ✓ Embedding normalization
- ✓ Similarity computation
- ✓ Long code truncation

### Vector Store Tests

- ✓ Index creation
- ✓ Vector addition
- ✓ Save/load index
- ✓ Save/load metadata
- ✓ Similarity search
- ✓ Score normalization
- ✓ Edge cases (empty index, k > size)

### Integration Tests

- ✓ End-to-end indexing workflow
- ✓ Repository with multiple files
- ✓ Index status checking
- ✓ Empty repository handling
- ✓ Error recovery

### Performance Tests

- ✓ Parsing speed (functions/second)
- ✓ Embedding generation speed
- ✓ Vector search latency
- ✓ Memory usage
- ✓ Full indexing performance
- ✓ Retrieval latency (P95, P99)

## Expected Performance Targets

- **Parsing**: > 50 functions/second
- **Embedding**: > 10 functions/second (with GPU)
- **Search**: < 100ms per query
- **Indexing**: < 15 minutes for 5,000 functions
- **Retrieval**: < 1 second average latency

## Troubleshooting

### "Model not available" errors

- Ensure internet connection for first download
- Check disk space (~500MB needed)
- Model downloads to `~/.cache/huggingface/`

### "Neo4j not available" errors

- Verify Neo4j is running: `http://localhost:7474`
- Check credentials match test configuration
- Ensure port 7687 is not blocked

### Import errors

- Run tests from the tests directory
- Ensure parent directories are in Python path
- Check all dependencies are installed

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run unit tests
  run: python run_tests.py unit

- name: Run integration tests
  run: |
    docker run -d -p 7687:7687 neo4j
    python run_tests.py integration
```

## Contributing

When adding new features:

1. Write unit tests for new components
2. Add integration tests for workflows
3. Update performance benchmarks if needed
4. Ensure all tests pass before committing
