# Implementation Plan

- [x] 1. Set up project structure and dependencies

  - Create `Feature_Components/KnowledgeBase/` directory structure
  - Add required dependencies to `requirements.txt` (tree-sitter, tree-sitter-python, transformers, torch, faiss-cpu, neo4j, numpy)
  - Create `__init__.py` files for Python package structure
  - _Requirements: 6.1, 6.2_

- [ ] 2. Implement Python code parser using tree-sitter

  - [x] 2.1 Create `parser.py` module with tree-sitter Python parser initialization

    - Write `PythonParser` class that loads tree-sitter-python grammar
    - Implement `parse_file(file_path)` method that returns AST
    - Handle parsing errors gracefully with logging
    - _Requirements: 5.5, 3.1_

  - [x] 2.2 Implement function extraction from AST

    - Write `extract_functions(ast, file_content)` method to find all function definitions
    - Extract function name, signature, start/end lines, and docstring
    - Handle both module-level and class-level functions
    - Return list of `FunctionInfo` dataclasses
    - _Requirements: 3.4, 2.2_

  - [x] 2.3 Implement class extraction from AST

    - Write `extract_classes(ast, file_content)` method to find all class definitions
    - Extract class name, start/end lines, and contained functions
    - Return list of `ClassInfo` dataclasses
    - _Requirements: 3.1_

  - [x] 2.4 Implement import and call relationship extraction

    - Write `extract_imports(ast)` to identify import statements
    - Write `extract_calls(ast)` to identify function calls within functions
    - Return dictionaries mapping functions to their imports and calls
    - _Requirements: 3.2_

- [ ] 3. Implement embedding generation pipeline

  - [x] 3.1 Create `embedder.py` module with embedding model wrapper

    - Write `CodeEmbedder` class that loads UniXcoder or GraphCodeBERT model
    - Implement `load_model(model_name)` method with caching
    - Add GPU/CPU device detection and model placement
    - _Requirements: 1.1, 8.3_

  - [x] 3.2 Implement function embedding generation

    - Write `embed_function(signature, docstring, body)` method
    - Concatenate signature, docstring, and function body for encoding
    - Tokenize and encode using the model
    - Return normalized embedding vector (768-dim)
    - _Requirements: 3.4, 2.5_

  - [x] 3.3 Implement batch embedding generation

    - Write `embed_batch(functions, batch_size=32)` method
    - Process functions in batches for efficiency
    - Handle tokenization padding and truncation
    - Return numpy array of embeddings
    - _Requirements: 5.3_

- [ ] 4. Implement Neo4j graph storage

  - [x] 4.1 Create `graph_store.py` module with Neo4j connection management

    - Write `GraphStore` class with Neo4j driver initialization
    - Implement connection pooling and error handling
    - Add methods for creating/clearing graph database
    - _Requirements: 3.1, 8.4_

  - [x] 4.2 Implement graph node creation methods

    - Write `create_file_node(file_info)` method
    - Write `create_class_node(class_info)` method
    - Write `create_function_node(function_info)` method
    - Use Cypher queries with proper parameterization
    - _Requirements: 3.1_

  - [x] 4.3 Implement graph relationship creation methods

    - Write `create_contains_relationship(parent_id, child_id)` method
    - Write `create_calls_relationship(caller_id, callee_id)` method
    - Write `create_imports_relationship(file_id, imported_file_id)` method
    - Batch relationship creation for performance
    - _Requirements: 3.2_

  - [x] 4.4 Implement graph query methods

    - Write `get_function_neighbors(function_id, relationship_type)` method
    - Write `get_file_functions(file_id)` method
    - Return structured data for future graph-based retrieval
    - _Requirements: 3.3_

- [ ] 5. Implement FAISS vector store

  - [x] 5.1 Create `vector_store.py` module with FAISS index management

    - Write `VectorStore` class with FAISS IndexFlatIP initialization
    - Implement `create_index(dimension=768)` method
    - Add methods for saving/loading index to/from disk
    - _Requirements: 8.1, 8.3_

  - [x] 5.2 Implement vector addition and metadata management

    - Write `add_vectors(embeddings, metadata)` method to add function embeddings
    - Maintain parallel metadata list with function information
    - Implement `save_metadata(metadata_path)` to write JSON file
    - Implement `load_metadata(metadata_path)` to read JSON file
    - _Requirements: 8.2_

  - [x] 5.3 Implement similarity search

    - Write `search(query_embedding, k=10)` method
    - Use FAISS inner product search for top-K retrieval
    - Return indices, scores, and corresponding metadata
    - Normalize scores to [0, 1] range
    - _Requirements: 1.1, 2.5_

- [ ] 6. Implement repository indexer orchestration

  - [x] 6.1 Create `indexer.py` module with main indexing logic

    - Write `RepositoryIndexer` class that coordinates all components
    - Initialize parser, embedder, graph store, and vector store
    - Implement repository traversal to find all Python files
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 6.2 Implement full repository indexing workflow

    - Write `index_repository(repo_path, repo_name)` method
    - Parse all Python files and extract functions/classes
    - Generate embeddings for all functions in batches
    - Create graph nodes and relationships
    - Build FAISS index and save metadata
    - Return `IndexResult` with statistics
    - _Requirements: 5.3, 5.4_

  - [x] 6.3 Implement indexing progress tracking and logging

    - Add progress logging for each major step (parsing, embedding, graph, index)
    - Track and report statistics (files processed, functions found, errors)
    - Measure and log indexing time
    - _Requirements: 8.5_

  - [x] 6.4 Implement error recovery and partial indexing

    - Skip files that fail to parse with warning
    - Continue indexing even if some files fail
    - Save partial results and track failed files in metadata
    - _Requirements: 5.5_

- [ ] 7. Implement issue processor

  - [x] 7.1 Create `issue_processor.py` module with text processing

    - Write `IssueProcessor` class with text cleaning methods
    - Implement `clean_text(text)` to remove markdown and special characters
    - Implement `normalize_text(text)` for lowercase and whitespace normalization
    - _Requirements: 7.1, 7.2_

  - [x] 7.2 Implement issue embedding generation

    - Write `process_issue(title, body)` method
    - Concatenate title and body, clean and normalize
    - Validate minimum text length (10 words)
    - Generate embedding using the same model as code
    - Return `ProcessedIssue` with cleaned text and embedding
    - _Requirements: 7.3, 7.4, 7.5_

- [ ] 8. Implement dense retriever

  - [x] 8.1 Create `retriever.py` module with retrieval logic

    - Write `DenseRetriever` class that loads vector store and metadata
    - Implement `load_index(repo_name, index_path, metadata_path)` method
    - Cache loaded indices in memory for fast access
    - _Requirements: 1.4, 8.3_

  - [x] 8.2 Implement retrieval method

    - Write `retrieve(issue_embedding, k=10)` method
    - Perform FAISS similarity search
    - Map indices to function metadata
    - Return list of `RetrievalResult` objects sorted by score
    - _Requirements: 1.1, 2.1, 2.2, 2.5_

- [ ] 9. Implement result formatter

  - [x] 9.1 Create `formatter.py` module with result formatting

    - Write `ResultFormatter` class for output formatting
    - Implement `aggregate_by_file(retrieval_results)` to group functions by file
    - Sort files by highest function score
    - _Requirements: 4.3, 2.3, 2.4_

  - [x] 9.2 Implement code snippet extraction

    - Write `extract_snippet(file_path, start_line, end_line)` method
    - Read file and extract specified line range
    - Handle file access errors gracefully
    - _Requirements: 4.2_

  - [x] 9.3 Implement JSON output formatting

    - Write `format_results(retrieval_results, repo_info)` method
    - Create structured JSON with top_files, functions, scores, and metadata
    - Include repository name, commit SHA, and timestamp
    - Match SPRINT's expected output format
    - _Requirements: 4.1, 4.4, 4.5_

- [ ] 10. Implement main Knowledge Base API

  - [x] 10.1 Create `knowledgeBase.py` module in Feature_Components/

    - Write main `BugLocalization(issue_title, issue_body, repo_owner, repo_name, repo_path, k=10)` function
    - Initialize all components (issue processor, retriever, formatter)
    - Implement lazy loading of models and indices
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 10.2 Implement end-to-end retrieval workflow

    - Check if repository is indexed, return error if not
    - Process issue text and generate embedding
    - Retrieve top-K functions using dense retriever
    - Format results for SPRINT comment generation
    - Handle all errors gracefully with logging
    - _Requirements: 1.1, 1.3, 6.4_

  - [x] 10.3 Implement repository indexing API

    - Write `IndexRepository(repo_path, repo_name)` function for manual indexing
    - Call repository indexer and return status
    - Store index files in standardized location
    - _Requirements: 5.1, 5.2, 6.5_

- [ ] 11. Create configuration and utilities

  - [x] 11.1 Create `config.py` with configuration constants

    - Define default model name (UniXcoder or GraphCodeBERT)
    - Define index storage paths
    - Define Neo4j connection parameters
    - Define batch sizes and performance parameters
    - _Requirements: 8.1, 8.4_

  - [x] 11.2 Create `utils.py` with helper functions

    - Write `get_commit_sha(repo_path)` to extract current commit
    - Write `validate_repo_path(repo_path)` for path validation
    - Write `generate_function_id(file_path, function_name, start_line)` for unique IDs
    - _Requirements: 5.4, 6.4_

- [ ] 12. Integration with SPRINT

  - [x] 12.1 Update SPRINT's processIssueEvents.py to use new Knowledge Base

    - Import `knowledgeBase.BugLocalization` function
    - Replace call to old `bugLocalization.BugLocalization` with new implementation
    - Pass repository path from existing code file retrieval
    - Handle case where repository is not indexed
    - _Requirements: 6.1, 6.3, 6.4_

  - [x] 12.2 Update or create comment generation for Knowledge Base results

    - Modify `createCommentBugLocalization.py` if needed for new result format
    - Format top files and functions into readable GitHub comment
    - Include confidence scores and line ranges
    - _Requirements: 6.5_

- [x] 13. Testing and validation

  - [x] 13.1 Create unit tests for parser module

    - Test function extraction on sample Python files
    - Test class extraction and nesting
    - Test import and call extraction
    - Verify error handling for malformed code

  - [x] 13.2 Create unit tests for embedder module

    - Test model loading and caching
    - Test single function embedding generation
    - Test batch embedding with various sizes
    - Verify embedding dimensions and normalization

  - [x] 13.3 Create unit tests for vector store

    - Test FAISS index creation and persistence
    - Test vector addition and search
    - Test metadata save/load
    - Verify top-K retrieval correctness

  - [x] 13.4 Create integration test for end-to-end workflow

    - Index a small test repository (10-20 Python files)
    - Process a test issue and retrieve results
    - Verify results contain expected functions
    - Validate output format matches SPRINT expectations

  - [x] 13.5 Create performance benchmarks

    - Measure indexing time for 1000 functions
    - Measure retrieval time for single query
    - Monitor memory usage during indexing and retrieval
    - Verify performance targets are met

## Phase 2 - SPRINT Integration

- [x] 14. Implement GitHub comment generation with structured formatting

  - [x] 14.1 Create `comment_generator.py` module with markdown formatting

    - Write `CommentGenerator` class that formats retrieval results as markdown
    - Implement `generate_comment(results, repo_info, confidence)` method
    - Create markdown template with confidence badges, code snippets, and links
    - Generate GitHub permalink URLs with line ranges
    - _Requirements: 10.2, 10.3, 10.4_

  - [x] 14.2 Implement code snippet formatting with syntax highlighting

    - Write `format_code_snippet(code, language, highlight_lines)` method
    - Use markdown code fencing with language specification
    - Add line number annotations
    - Include context lines around highlighted sections
    - _Requirements: 10.2_

  - [x] 14.3 Implement confidence badge formatting

    - Write `format_confidence_badge(confidence, score)` method
    - Use emoji indicators (🟢 High, 🟡 Medium, 🔴 Low)
    - Include calibrated probability percentage
    - _Requirements: 10.5_

- [x] 15. Implement telemetry logging system

  - [x] 15.1 Create `telemetry.py` module with structured logging

    - Write `TelemetryLogger` class with JSON-formatted logging
    - Implement `log_retrieval(issue_id, latency, top_k, confidence)` method
    - Implement `log_indexing(repo_name, files, duration)` method
    - Configure log rotation and retention
    - _Requirements: 11.1, 11.2, 11.3_

  - [x] 15.2 Implement aggregate statistics computation

    - Write `get_statistics(time_range)` method to compute metrics
    - Calculate average latency, success rate, confidence distribution
    - Generate summary reports for monitoring
    - _Requirements: 11.4_

  - [x] 15.3 Implement error tracking and alerting

    - Log all errors with context (issue ID, repo, stack trace)
    - Track error rates by type
    - Implement basic alerting for high error rates
    - _Requirements: 11.5_

- [x] 16. Update SPRINT integration for Phase 2

  - [x] 16.1 Modify processIssueEvents.py to pass commit_sha

    - Extract commit_sha from repository information
    - Pass commit_sha to BugLocalization() function
    - Handle cases where commit_sha is unavailable
    - _Requirements: 9.3_

  - [x] 16.2 Update createCommentBugLocalization.py for new format

    - Integrate with CommentGenerator for markdown formatting
    - Post structured comments to GitHub issues
    - Handle comment posting errors with retries
    - _Requirements: 10.1, 10.2_

  - [x] 16.3 Implement end-to-end latency monitoring

    - Add timing instrumentation to processIssueEvents.py
    - Log total time from webhook to comment posted
    - Alert if latency exceeds 10 second threshold
    - _Requirements: 9.4_

  - [x] 16.4 Add compatibility checks for existing features

    - Verify duplicate detection still works
    - Verify severity prediction still works
    - Test all three features running together
    - _Requirements: 9.5_

- [x] 17. Create Phase 2 integration tests

  - [x] 17.1 Test GitHub comment generation

    - Create test cases with sample retrieval results
    - Verify markdown formatting is correct
    - Check permalink URLs are valid
    - Validate confidence badges display correctly

  - [x] 17.2 Test telemetry logging

    - Verify logs written in correct JSON format
    - Check aggregate statistics computation
    - Test log rotation and retention

  - [x] 17.3 Test end-to-end SPRINT workflow

    - Simulate GitHub webhook with test issue
    - Verify comment posted within 10 seconds
    - Check telemetry logs written
    - Validate no interference with other features

## Phase 3 - Line-Level Localization

- [x] 18. Implement line window generation and embedding

  - [x] 18.1 Create `window_generator.py` module for window extraction

    - Write `WindowGenerator` class with tokenization logic
    - Implement `generate_windows(function_body, window_size, stride)` method
    - Create overlapping windows with 50% overlap (e.g., 48 tokens, 24 stride)
    - Map token positions back to line numbers
    - _Requirements: 12.1, 12.2_

  - [x] 18.2 Implement window embedding generation

    - Write `embed_windows(windows, batch_size=64)` method
    - Use same embedding model as functions
    - Process windows in batches for efficiency
    - Return embeddings with window metadata
    - _Requirements: 12.1_

  - [x] 18.3 Create window FAISS index

    - Extend VectorStore to support window indices
    - Write `create_window_index(window_embeddings, metadata)` method
    - Save window index and metadata separately from function index
    - _Requirements: 12.1_

  - [x] 18.4 Integrate window generation into indexing pipeline

    - Modify RepositoryIndexer to generate windows during indexing
    - Add window generation after function extraction
    - Track window count in IndexResult
    - _Requirements: 12.1_

- [x] 19. Implement line-level reranker

  - [x] 19.1 Create `line_reranker.py` module with reranking logic

    - Write `LineReranker` class that loads window index
    - Implement `load_window_index(repo_name, index_path)` method
    - Cache window indices in memory
    - _Requirements: 12.3_

  - [x] 19.2 Implement two-stage retrieval workflow

    - Write `rerank_functions(issue_embedding, function_results)` method
    - For each top function, retrieve all its windows from index
    - Compute similarity between issue embedding and window embeddings
    - Select best window per function
    - _Requirements: 12.3, 12.4_

  - [x] 19.3 Implement line range extraction

    - Write `extract_line_range(window_metadata)` method
    - Map window token positions to line numbers
    - Include context lines before and after
    - Return LineResult with snippet
    - _Requirements: 12.4_

  - [x] 19.4 Integrate line reranker into main API

    - Modify BugLocalization() to call line reranker after function retrieval
    - Add line-level results to output format
    - Make line-level localization optional (configurable)
    - _Requirements: 12.3_

- [x] 20. Update comment generation for line-level results

  - [x] 20.1 Modify CommentGenerator to include line highlights

    - Update markdown template to show specific line ranges
    - Add visual indicators for highlighted lines (e.g., ⚠️)
    - Include line numbers in code snippets
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 20.2 Implement syntax highlighting for snippets

    - Use markdown code fencing with language specification
    - Format line-level snippets with proper indentation
    - Add context lines with different styling
    - _Requirements: 13.5_

- [ ] 21. Validate line-level localization accuracy

  - [ ] 21.1 Create validation dataset with known buggy lines

    - Collect issues with known bug locations
    - Annotate ground truth line ranges
    - Prepare test cases for IoU computation

  - [ ] 21.2 Implement IoU metric computation

    - Write `compute_iou(predicted_range, ground_truth_range)` function
    - Calculate IoU for each test case
    - Compute aggregate statistics

  - [ ] 21.3 Validate Phase 3 accuracy target

    - Run line-level localization on validation set
    - Verify IoU ≥ 0.5 on at least 40% of correctly localized functions
    - Analyze failure cases and document findings
    - _Requirements: 12.5_

## Phase 4 - Confidence Calibration

- [x] 22. Implement confidence calibration system

  - [x] 22.1 Create `calibrator.py` module with calibration logic

    - Write `ConfidenceCalibrator` class with threshold management
    - Implement `load_calibration_config(config_path)` method
    - Define default thresholds for High/Medium/Low confidence
    - _Requirements: 14.1, 14.2_

  - [x] 22.2 Implement calibration curve computation

    - Write `compute_calibration(validation_results)` method
    - Collect similarity scores and ground truth labels from validation set
    - Compute precision@3 for different score thresholds
    - Find thresholds where precision@3 ≥ 0.9 (High), ≥ 0.7 (Medium)
    - _Requirements: 14.1, 14.3_

  - [x] 22.3 Implement score-to-confidence mapping

    - Write `calibrate_score(similarity_score)` method
    - Map raw similarity score to confidence level (High/Medium/Low)
    - Return calibrated probability based on validation data
    - _Requirements: 14.2, 14.5_

  - [x] 22.4 Create calibration configuration file

    - Define JSON schema for calibration config
    - Store thresholds and validation statistics
    - Include model version and validation date
    - _Requirements: 14.1_

- [x] 23. Integrate confidence calibration into retrieval pipeline

  - [x] 23.1 Modify DenseRetriever to include confidence

    - Update retrieve() method to call calibrator
    - Add confidence and confidence_score to RetrievalResult
    - Ensure confidence computed for all results
    - _Requirements: 14.5_

  - [x] 23.2 Modify LineReranker to include confidence

    - Update rerank_functions() to call calibrator
    - Add confidence to LineResult
    - Use same calibration thresholds as function-level
    - _Requirements: 14.5_

  - [x] 23.3 Update result formatting to include confidence

    - Modify ResultFormatter to include confidence in output
    - Add confidence to JSON response
    - Update comment generation to show confidence
    - _Requirements: 14.4, 14.5_

- [x] 24. Implement auto-labeling system

  - [x] 24.1 Create `auto_labeler.py` module with GitHub API integration

    - Write `AutoLabeler` class with GitHub authentication
    - Use SPRINT's existing app_authentication.py for credentials
    - Implement connection pooling for API calls
    - _Requirements: 15.1, 15.2_

  - [x] 24.2 Implement label creation and management

    - Write `ensure_labels_exist()` method to create confidence labels
    - Create labels: "bug-localization:high-confidence", "bug-localization:medium-confidence", "bug-localization:low-confidence"
    - Set appropriate colors and descriptions for labels
    - _Requirements: 15.2_

  - [x] 24.3 Implement label application logic

    - Write `apply_confidence_label(issue_number, confidence)` method
    - Remove old confidence labels before applying new one
    - Handle GitHub API rate limiting with exponential backoff
    - Retry failed operations up to 3 times
    - _Requirements: 15.1, 15.3, 15.4_

  - [x] 24.4 Integrate auto-labeling into main workflow

    - Call AutoLabeler after bug localization completes
    - Apply label based on highest confidence result
    - Log all labeling actions for audit
    - _Requirements: 15.5_

- [ ] 25. Validate confidence calibration accuracy

  - [ ] 25.1 Run calibration on validation dataset

    - Prepare validation set with known bug locations
    - Run retrieval and collect scores
    - Compute calibration curve and thresholds

  - [ ] 25.2 Validate High confidence precision target

    - Filter results with High confidence
    - Check if true bug is in Top-3 for each
    - Verify precision@3 ≥ 90%
    - _Requirements: 14.3_

  - [ ] 25.3 Test auto-labeling on test repository

    - Create test issues with different confidence levels
    - Verify correct labels applied
    - Check label removal and updates work correctly

## Phase 5 - Incremental Indexing

- [x] 26. Implement git diff analysis and change detection

  - [x] 26.1 Create `incremental_indexer.py` module with git operations

    - Write `IncrementalIndexer` class with GitPython integration
    - Implement `get_changed_files(old_commit, new_commit)` method
    - Use git diff to identify added, modified, and deleted files
    - _Requirements: 16.2_

  - [x] 26.2 Implement dependency analysis

    - Write `get_dependent_files(changed_files)` method
    - Use import graph from Neo4j to find files that import changed files
    - Include dependents in reindexing list
    - _Requirements: 16.2_

  - [x] 26.3 Implement file change classification

    - Classify changes as added, modified, or deleted
    - Handle file renames and moves
    - Track change statistics for logging
    - _Requirements: 16.2_

- [x] 27. Implement incremental index updates

  - [x] 27.1 Implement function removal from indices

    - Write `remove_functions(function_ids)` method for VectorStore
    - Remove embeddings from FAISS index
    - Update metadata to reflect removals
    - Remove nodes from Neo4j graph
    - _Requirements: 16.3_

  - [x] 27.2 Implement selective reindexing

    - Write `update_index(old_commit, new_commit)` method
    - For each changed file: remove old functions, parse new functions, add new embeddings
    - Update graph relationships for changed files
    - Regenerate windows for changed functions
    - _Requirements: 16.3, 16.4_

  - [x] 27.3 Implement delta index creation

    - Write `create_delta_index(base_commit, new_commit)` method
    - Store only differences from base index
    - Include metadata linking to parent commit
    - _Requirements: 16.5_

  - [x] 27.4 Optimize index merging

    - Implement efficient FAISS index merging
    - Minimize memory usage during updates
    - Use temporary indices for atomic updates
    - _Requirements: 16.4_

- [x] 28. Implement version-specific retrieval

  - [x] 28.1 Create index registry for version management

    - Write `IndexRegistry` class to track all indices
    - Implement `register_index(commit_sha, index_info)` method
    - Store registry as JSON file
    - _Requirements: 17.2_

  - [x] 28.2 Implement commit-specific index loading

    - Modify DenseRetriever to accept commit_sha parameter
    - Write `load_index_for_commit(repo_name, commit_sha)` method
    - Load appropriate function and window indices
    - _Requirements: 17.1, 17.3_

  - [x] 28.3 Update BugLocalization API for version support

    - Accept optional commit_sha parameter (default: HEAD)
    - Load index for specified commit
    - Return error if commit not indexed
    - _Requirements: 17.1, 17.4, 17.5_

- [ ] 29. Implement index pruning and storage management

  - [ ] 29.1 Implement index pruning logic

    - Write `prune_old_indices(retention_days)` method
    - Identify indices older than retention period
    - Delete old index files and update registry
    - _Requirements: 18.2_

  - [ ] 29.2 Implement index compression

    - Write `compress_index(index_path)` method
    - Use FAISS quantization for older indices
    - Reduce storage footprint while maintaining accuracy
    - _Requirements: 18.3_

  - [ ] 29.3 Implement storage monitoring

    - Write `get_storage_stats()` method
    - Calculate total storage used by indices
    - Track storage per repository and per commit
    - Log storage statistics for monitoring
    - _Requirements: 18.5_

  - [ ] 29.4 Implement index management commands

    - Write `list_indices(repo_name)` method to show all indices
    - Write `delete_index(commit_sha)` method for manual cleanup
    - Provide CLI or API for index management
    - _Requirements: 18.4_

- [ ] 30. Integrate incremental indexing with GitHub webhooks

  - [ ] 30.1 Add push event handler to SPRINT

    - Modify processIssueEvents.py to handle push events
    - Extract old and new commit SHAs from push payload
    - Call IncrementalIndexer.update_index()
    - _Requirements: 16.1_

  - [ ] 30.2 Implement async indexing for push events

    - Use background task queue for indexing
    - Avoid blocking webhook response
    - Log indexing progress and completion
    - _Requirements: 16.1_

  - [ ] 30.3 Handle indexing failures gracefully

    - Implement fallback to full reindexing on failure
    - Log errors with context
    - Alert on repeated failures
    - _Requirements: 16.4_

- [ ] 31. Validate incremental indexing performance

  - [ ] 31.1 Test incremental update latency

    - Simulate push events with varying numbers of changed files
    - Measure update time for < 20 changed files
    - Verify target of < 2 seconds met
    - _Requirements: 16.4_

  - [ ] 31.2 Test version-specific retrieval

    - Index multiple commits for test repository
    - Run retrieval against different commits
    - Verify correct results for each version
    - _Requirements: 17.4_

  - [ ] 31.3 Test storage efficiency

    - Measure storage usage for delta indices
    - Verify compression reduces footprint
    - Test pruning removes old indices correctly
    - _Requirements: 18.1, 18.2, 18.3_

## Final Integration and Testing

- [ ] 32. End-to-end testing of all phases

  - [ ] 32.1 Test complete workflow on real repository

    - Index a real open-source repository
    - Process real GitHub issues
    - Verify comments posted with all features (function-level, line-level, confidence, labels)
    - Check telemetry logs

  - [ ] 32.2 Test incremental updates with real commits

    - Make code changes and push
    - Verify incremental indexing triggers
    - Process new issue and verify updated results

  - [ ] 32.3 Performance validation

    - Verify end-to-end latency < 10 seconds
    - Check incremental indexing < 2 seconds
    - Validate storage usage within targets

  - [ ] 32.4 Compatibility testing

    - Verify duplicate detection still works
    - Verify severity prediction still works
    - Test all SPRINT features together
