# Automatic Knowledge Base Updates - Architecture

## Current State (Without Auto-Update)

```
Developer pushes code
         │
         ▼
    GitHub Repo
         │
         │ (No connection)
         │
         ✗ Knowledge Base NOT updated
         │
         │
    New Issue Created
         │
         ▼
    Bug Localization
         │
         ▼
    Uses OLD index ⚠️
    (May return outdated results)
```

## Desired State (With Auto-Update)

```
Developer pushes code
         │
         ▼
    GitHub Repo
         │
         │ Push Event Webhook
         ▼
┌─────────────────────────────────────────┐
│     Push Event Handler                  │
│  1. Detect changes (git diff)           │
│  2. Classify: added/modified/deleted    │
│  3. Decide: incremental vs full         │
└────────────┬────────────────────────────┘
             │
             ├─── Few changes (< 50 files)
             │         │
             │         ▼
             │    ┌─────────────────────────┐
             │    │ Incremental Update      │
             │    │ • Parse changed files   │
             │    │ • Update embeddings     │
             │    │ • Update FAISS index    │
             │    │ • Update graph          │
             │    │ Time: < 10 seconds      │
             │    └─────────────────────────┘
             │
             └─── Many changes (≥ 50 files)
                       │
                       ▼
                  ┌─────────────────────────┐
                  │ Full Re-index           │
                  │ • Parse all files       │
                  │ • Generate embeddings   │
                  │ • Rebuild FAISS index   │
                  │ • Rebuild graph         │
                  │ Time: 5-20 minutes      │
                  └─────────────────────────┘
                       │
                       ▼
              Knowledge Base UPDATED ✓
                       │
                       │
              New Issue Created
                       │
                       ▼
              Bug Localization
                       │
                       ▼
              Uses CURRENT index ✓
              (Accurate results)
```

## Detailed Flow: Incremental Update

```
┌─────────────────────────────────────────────────────────────┐
│                    Push Event Received                       │
│  Payload: {                                                  │
│    before: "abc123",                                         │
│    after: "def456",                                          │
│    commits: [...],                                           │
│    repository: {...}                                         │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 1: Get Changed Files                       │
│  $ git diff --name-only abc123 def456                       │
│                                                              │
│  Output:                                                     │
│    src/processor.py          (modified)                      │
│    src/validator.java        (modified)                      │
│    src/utils.py              (added)                         │
│    src/old_module.py         (deleted)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 2: Classify Changes                        │
│                                                              │
│  Added:    [src/utils.py]                                   │
│  Modified: [src/processor.py, src/validator.java]           │
│  Deleted:  [src/old_module.py]                              │
│                                                              │
│  Total: 4 files                                             │
│  Decision: Incremental update (< 50 files)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 3: Process Changes                         │
│                                                              │
│  For each ADDED file:                                        │
│    1. Detect language (Python/Java)                         │
│    2. Parse with appropriate parser                         │
│    3. Extract functions/methods                             │
│    4. Generate embeddings                                   │
│    5. Add to FAISS index                                    │
│    6. Add to graph database                                 │
│                                                              │
│  For each MODIFIED file:                                     │
│    1. Remove old functions from index                       │
│    2. Parse new version                                     │
│    3. Extract functions/methods                             │
│    4. Generate embeddings                                   │
│    5. Update FAISS index                                    │
│    6. Update graph database                                 │
│                                                              │
│  For each DELETED file:                                      │
│    1. Remove all functions from index                       │
│    2. Remove from graph database                            │
│    3. Update metadata                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 4: Update Storage                          │
│                                                              │
│  FAISS Index:                                                │
│    • Remove vectors for deleted/modified functions          │
│    • Add vectors for new/modified functions                 │
│    • Save updated index                                     │
│                                                              │
│  Metadata:                                                   │
│    • Update function count                                  │
│    • Update commit SHA                                      │
│    • Update timestamp                                       │
│    • Update language statistics                             │
│                                                              │
│  Graph Database:                                             │
│    • Remove old nodes and relationships                     │
│    • Add new nodes and relationships                        │
│    • Update file nodes                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 5: Verify Update                           │
│                                                              │
│  ✓ Index updated successfully                               │
│  ✓ 3 functions added                                        │
│  ✓ 5 functions modified                                     │
│  ✓ 2 functions deleted                                      │
│  ✓ Time: 8.5 seconds                                        │
│                                                              │
│  New state:                                                  │
│    Commit: def456                                           │
│    Functions: 758 (was 752)                                 │
│    Languages: {python: 505, java: 253}                      │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Webhook                            │
│                  POST /webhook                               │
│                  X-GitHub-Event: push                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Flask Route Handler                         │
│  @app.route('/webhook', methods=['POST'])                   │
│  def webhook():                                              │
│      if event_type == 'push':                                │
│          executor.submit(process_push_event, ...)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Background Task Executor                        │
│  ThreadPoolExecutor (4 workers)                              │
│  • Non-blocking webhook response                            │
│  • Parallel processing of multiple repos                    │
│  • Error isolation                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              processPushEvents.py                            │
│                                                              │
│  def process_push_event(repo_full_name, payload):           │
│      1. Extract commit info                                 │
│      2. Clone/update repository                             │
│      3. Check if indexed                                    │
│      4. Decide: incremental vs full                         │
│      5. Execute update                                      │
│      6. Log results                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─── Not indexed yet
                     │         │
                     │         ▼
                     │    ┌─────────────────────────────────┐
                     │    │  IndexRepository()              │
                     │    │  (Full indexing)                │
                     │    └─────────────────────────────────┘
                     │
                     └─── Already indexed
                               │
                               ▼
                          ┌─────────────────────────────────┐
                          │  IncrementalIndexer             │
                          │  • get_changed_files()          │
                          │  • classify_changes()           │
                          │  • update_index()               │
                          └─────────────────────────────────┘
```

## Data Flow: Before and After

### Before (Manual Update)

```
Time: T0
┌──────────────────┐
│  Repository      │  Commit: abc123
│  Functions: 100  │
└──────────────────┘
         │
         │ Manual Index
         ▼
┌──────────────────┐
│  Knowledge Base  │  Commit: abc123
│  Functions: 100  │
└──────────────────┘

Time: T1 (Developer pushes code)
┌──────────────────┐
│  Repository      │  Commit: def456
│  Functions: 105  │  ← 5 new functions
└──────────────────┘
         │
         ✗ No update
         │
┌──────────────────┐
│  Knowledge Base  │  Commit: abc123  ⚠️ STALE
│  Functions: 100  │  ← Missing 5 functions
└──────────────────┘

Time: T2 (Issue created)
┌──────────────────┐
│  Bug Localization│
│  Uses old index  │  ← May miss relevant code
└──────────────────┘
```

### After (Automatic Update)

```
Time: T0
┌──────────────────┐
│  Repository      │  Commit: abc123
│  Functions: 100  │
└──────────────────┘
         │
         │ Initial Index
         ▼
┌──────────────────┐
│  Knowledge Base  │  Commit: abc123
│  Functions: 100  │
└──────────────────┘

Time: T1 (Developer pushes code)
┌──────────────────┐
│  Repository      │  Commit: def456
│  Functions: 105  │  ← 5 new functions
└──────────────────┘
         │
         │ Push Event → Auto Update (8 seconds)
         ▼
┌──────────────────┐
│  Knowledge Base  │  Commit: def456  ✓ CURRENT
│  Functions: 105  │  ← All functions indexed
└──────────────────┘

Time: T2 (Issue created)
┌──────────────────┐
│  Bug Localization│
│  Uses new index  │  ← Accurate results
└──────────────────┘
```

## Performance Comparison

### Incremental Update

```
┌─────────────────────────────────────────────────────────────┐
│  Scenario: 5 files changed out of 1000                      │
│                                                              │
│  Without Incremental:                                        │
│    • Re-index all 1000 files                                │
│    • Parse 1000 files                                       │
│    • Generate 5000 embeddings                               │
│    • Rebuild entire FAISS index                             │
│    • Time: ~15 minutes                                      │
│                                                              │
│  With Incremental:                                           │
│    • Re-index only 5 files                                  │
│    • Parse 5 files                                          │
│    • Generate 25 embeddings                                 │
│    • Update FAISS index (add/remove)                        │
│    • Time: ~10 seconds                                      │
│                                                              │
│  Speedup: 90x faster! 🚀                                    │
└─────────────────────────────────────────────────────────────┘
```

### Update Time by Change Size

| Files Changed | Full Re-index | Incremental | Speedup   |
| ------------- | ------------- | ----------- | --------- |
| 1-5 files     | 15 min        | 5-10 sec    | 90x       |
| 6-20 files    | 15 min        | 20-40 sec   | 22x       |
| 21-50 files   | 15 min        | 1-2 min     | 10x       |
| 50+ files     | 15 min        | 15 min      | 1x (full) |

## Error Handling

```
┌─────────────────────────────────────────────────────────────┐
│                    Error Scenarios                           │
│                                                              │
│  1. Git Operation Fails                                      │
│     → Log error                                              │
│     → Retry once                                             │
│     → Fall back to full clone                               │
│                                                              │
│  2. Parsing Fails                                            │
│     → Skip problematic file                                 │
│     → Log warning                                            │
│     → Continue with other files                             │
│                                                              │
│  3. Embedding Generation Fails                               │
│     → Retry with smaller batch                              │
│     → Log error                                              │
│     → Skip if persistent                                    │
│                                                              │
│  4. Index Update Fails                                       │
│     → Rollback to previous index                            │
│     → Log error                                              │
│     → Alert administrator                                   │
│                                                              │
│  5. Too Many Failures                                        │
│     → Fall back to full re-index                            │
│     → Send alert                                             │
│     → Log for investigation                                 │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Base Update Metrics                   │
│                                                              │
│  Last Update:        2 minutes ago                          │
│  Update Type:        Incremental                            │
│  Files Changed:      3                                      │
│  Functions Updated:  7                                      │
│  Update Time:        8.5 seconds                            │
│  Status:             ✓ Success                              │
│                                                              │
│  Repository:         owner/repo                             │
│  Current Commit:     def456                                 │
│  Total Functions:    758                                    │
│  Languages:          Python (505), Java (253)               │
│                                                              │
│  Recent Updates:                                             │
│    ✓ 2 min ago  - Incremental (3 files, 8.5s)             │
│    ✓ 1 hour ago - Incremental (1 file, 5.2s)              │
│    ✓ 3 hours ago - Incremental (7 files, 15.3s)           │
│    ✓ 1 day ago  - Full re-index (150 files, 12m)          │
│                                                              │
│  Health:                                                     │
│    Success Rate:     98.5%                                  │
│    Avg Update Time:  9.2 seconds                            │
│    Failed Updates:   2 (last 30 days)                      │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

```python
# config.py

# Incremental Update Settings
INCREMENTAL_UPDATE_ENABLED = True
MAX_FILES_FOR_INCREMENTAL = 50  # Switch to full re-index above this
UPDATE_TIMEOUT_SECONDS = 300    # 5 minutes max
RETRY_FAILED_UPDATES = True
MAX_RETRIES = 2

# Repository Management
REPO_STORAGE_PATH = "Data_Storage/Repositories"
AUTO_CLONE_REPOS = True
KEEP_REPO_HISTORY = True

# Performance
PARALLEL_FILE_PROCESSING = True
MAX_PARALLEL_FILES = 4
BATCH_SIZE_INCREMENTAL = 16  # Smaller batches for incremental

# Monitoring
LOG_ALL_UPDATES = True
ALERT_ON_FAILURE = True
METRICS_RETENTION_DAYS = 30
```

## Summary

**Current State:**

- ❌ No automatic updates
- ❌ Manual re-indexing required
- ❌ Risk of stale results

**With Auto-Update:**

- ✅ Automatic updates on push
- ✅ Fast incremental updates (< 10 seconds)
- ✅ Always current results
- ✅ Fallback to full re-index when needed

**Implementation Effort:**

- Foundation: Already built ✓
- Push handler: ~200 lines of code
- Testing: 1-2 hours
- Total: ~4 hours of work

The infrastructure is ready - just needs to be wired up to GitHub push events! 🎯
