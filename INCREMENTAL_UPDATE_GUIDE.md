# Incremental Knowledge Base Updates - Implementation Guide

## Current Limitation

**The knowledge base does NOT automatically update when you push new commits to GitHub.**

This means:

- ❌ New commits don't trigger re-indexing
- ❌ Code changes aren't reflected in bug localization
- ❌ New functions/methods aren't added to the index
- ❌ Deleted code may still appear in results

## Solution: Implement Incremental Updates

### Option 1: Manual Re-indexing (Current Workaround)

After making changes to your repository, manually re-index:

```python
from Feature_Components.knowledgeBase import IndexRepository

# Re-index after code changes
result = IndexRepository(
    repo_path="path/to/your/repo",
    repo_name="owner/repo"
)

print(f"Re-indexed {result['total_functions']} functions")
```

**Pros:**

- ✅ Simple and reliable
- ✅ Full control over when to update
- ✅ Works immediately

**Cons:**

- ❌ Manual process
- ❌ Time-consuming for large repos
- ❌ Easy to forget

---

### Option 2: Automatic Incremental Updates (Recommended)

Enable automatic updates on every push event.

#### Step 1: Add Push Event Handler

Create a new file: `SPRINT Tool/GitHub_Event_Handler/processPushEvents.py`

```python
"""
Process GitHub push events for incremental knowledge base updates
"""

import logging
import time
from Feature_Components.KnowledgeBase.incremental_indexer import IncrementalIndexer
from Feature_Components.knowledgeBase import IndexRepository
from .app_authentication import authenticate_github_app

logger = logging.getLogger(__name__)


def process_push_event(repo_full_name, push_payload):
    """
    Process a GitHub push event and update the knowledge base

    Args:
        repo_full_name: Full repository name (owner/repo)
        push_payload: GitHub push event payload
    """
    try:
        logger.info(f"Processing push event for {repo_full_name}")

        # Extract commit information
        before_commit = push_payload.get('before')
        after_commit = push_payload.get('after')
        commits = push_payload.get('commits', [])

        logger.info(f"Push: {before_commit[:7]} → {after_commit[:7]} ({len(commits)} commits)")

        # Get repository path (you'll need to clone/update it)
        repo_path = get_or_clone_repository(repo_full_name, after_commit)

        # Check if repository is already indexed
        from Feature_Components.knowledgeBase import GetIndexStatus
        status = GetIndexStatus(repo_full_name)

        if not status or not status.get('indexed'):
            # First time indexing - do full index
            logger.info(f"Repository not indexed yet, performing full indexing...")
            result = IndexRepository(
                repo_path=repo_path,
                repo_name=repo_full_name
            )
            logger.info(f"Full indexing complete: {result['total_functions']} functions")
            return {
                'success': True,
                'type': 'full_index',
                'functions': result['total_functions']
            }

        # Incremental update
        logger.info(f"Performing incremental update...")
        indexer = IncrementalIndexer(repo_path)

        # Get changed files
        added, modified, deleted = indexer.get_changed_files(before_commit, after_commit)

        total_changes = len(added) + len(modified) + len(deleted)
        logger.info(f"Changes detected: {len(added)} added, {len(modified)} modified, {len(deleted)} deleted")

        # If too many changes, do full re-index
        if total_changes > 50:
            logger.info(f"Too many changes ({total_changes}), performing full re-index...")
            result = IndexRepository(
                repo_path=repo_path,
                repo_name=repo_full_name
            )
            return {
                'success': True,
                'type': 'full_reindex',
                'reason': 'too_many_changes',
                'changes': total_changes,
                'functions': result['total_functions']
            }

        # Perform incremental update
        update_result = indexer.update_index(before_commit, after_commit)

        logger.info(f"Incremental update complete: {update_result['functions_updated']} functions updated")

        return {
            'success': True,
            'type': 'incremental',
            'added': len(added),
            'modified': len(modified),
            'deleted': len(deleted),
            'functions_updated': update_result['functions_updated'],
            'time_seconds': update_result['update_time_seconds']
        }

    except Exception as e:
        logger.error(f"Failed to process push event: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def get_or_clone_repository(repo_full_name, commit_sha):
    """
    Get local repository path, cloning if necessary

    Args:
        repo_full_name: Full repository name (owner/repo)
        commit_sha: Commit SHA to checkout

    Returns:
        Local path to repository
    """
    import os
    import subprocess
    from pathlib import Path

    # Define local storage path
    repos_dir = Path("Data_Storage/Repositories")
    repos_dir.mkdir(parents=True, exist_ok=True)

    repo_path = repos_dir / repo_full_name.replace('/', '_')

    if not repo_path.exists():
        # Clone repository
        logger.info(f"Cloning repository {repo_full_name}...")
        clone_url = f"https://github.com/{repo_full_name}.git"

        subprocess.run(
            ['git', 'clone', clone_url, str(repo_path)],
            check=True,
            capture_output=True
        )
    else:
        # Update existing repository
        logger.info(f"Updating repository {repo_full_name}...")
        subprocess.run(
            ['git', 'fetch', 'origin'],
            cwd=repo_path,
            check=True,
            capture_output=True
        )

    # Checkout specific commit
    subprocess.run(
        ['git', 'checkout', commit_sha],
        cwd=repo_path,
        check=True,
        capture_output=True
    )

    return str(repo_path)
```

#### Step 2: Update Main Event Handler

Modify `SPRINT Tool/main.py` to handle push events:

```python
# Add to main.py

from GitHub_Event_Handler.processPushEvents import process_push_event

@app.route('/webhook', methods=['POST'])
def webhook():
    # ... existing code ...

    event_type = request.headers.get('X-GitHub-Event')

    if event_type == 'issues':
        # Existing issue handling
        process_issue_event(...)

    elif event_type == 'push':
        # NEW: Handle push events
        payload = request.json
        repo_full_name = payload['repository']['full_name']

        # Process push in background
        executor.submit(process_push_event, repo_full_name, payload)

        return jsonify({'status': 'processing'}), 200

    # ... rest of code ...
```

#### Step 3: Update GitHub App Webhook Settings

1. Go to your GitHub App settings
2. Subscribe to **Push** events:

   - ☑ Push

3. Save changes

#### Step 4: Test the Integration

```bash
# 1. Make a code change
echo "# Test change" >> README.md
git add README.md
git commit -m "Test incremental update"
git push

# 2. Check logs
tail -f logs/sprint.log

# Expected output:
# Processing push event for owner/repo
# Changes detected: 0 added, 1 modified, 0 deleted
# Incremental update complete: 0 functions updated
```

---

### Option 3: Scheduled Re-indexing

Re-index repositories on a schedule (e.g., nightly).

#### Create Scheduled Task

```python
# scheduled_reindex.py
import schedule
import time
from Feature_Components.knowledgeBase import IndexRepository

def reindex_all_repositories():
    """Re-index all tracked repositories"""
    repositories = [
        ("path/to/repo1", "owner/repo1"),
        ("path/to/repo2", "owner/repo2"),
    ]

    for repo_path, repo_name in repositories:
        print(f"Re-indexing {repo_name}...")
        try:
            result = IndexRepository(repo_path, repo_name)
            print(f"  ✓ Indexed {result['total_functions']} functions")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

# Schedule daily at 2 AM
schedule.every().day.at("02:00").do(reindex_all_repositories)

print("Scheduler started. Press Ctrl+C to stop.")
while True:
    schedule.run_pending()
    time.sleep(60)
```

Run as a background service:

```bash
# Linux/Mac
nohup python scheduled_reindex.py &

# Windows
pythonw scheduled_reindex.py
```

---

## Comparison of Options

| Feature           | Manual      | Automatic (Push) | Scheduled        |
| ----------------- | ----------- | ---------------- | ---------------- |
| Setup Complexity  | ⭐ Easy     | ⭐⭐⭐ Complex   | ⭐⭐ Medium      |
| Real-time Updates | ❌ No       | ✅ Yes           | ❌ No            |
| Resource Usage    | Low         | Medium           | Low              |
| Reliability       | High        | Medium           | High             |
| Best For          | Development | Production       | Batch Processing |

---

## Implementation Status

### What's Already Built (Phase 5 Foundation):

```python
# SPRINT Tool/Feature_Components/KnowledgeBase/incremental_indexer.py
class IncrementalIndexer:
    ✅ get_changed_files(old_commit, new_commit)
    ✅ classify_changes(changed_files)
    ✅ update_index(old_commit, new_commit)
    ✅ Fallback to full reindex for large changes
```

```python
# SPRINT Tool/Feature_Components/KnowledgeBase/index_registry.py
class IndexRegistry:
    ✅ Track multiple versions
    ✅ Store commit SHAs
    ✅ Manage index metadata
```

### What Needs to Be Added:

1. ❌ Push event webhook handler
2. ❌ Repository cloning/updating logic
3. ❌ Background task processing
4. ❌ Error handling and retry logic
5. ❌ Monitoring and alerts

---

## Quick Start: Enable Automatic Updates

### Minimal Implementation (5 minutes)

Add this to `main.py`:

```python
@app.route('/webhook', methods=['POST'])
def webhook():
    event_type = request.headers.get('X-GitHub-Event')
    payload = request.json

    if event_type == 'push':
        repo_full_name = payload['repository']['full_name']

        # Simple: Just re-index on every push
        def reindex():
            try:
                # Assuming repo is already cloned locally
                repo_path = f"repos/{repo_full_name.replace('/', '_')}"
                IndexRepository(repo_path, repo_full_name)
                logger.info(f"Re-indexed {repo_full_name}")
            except Exception as e:
                logger.error(f"Re-index failed: {e}")

        # Run in background
        executor.submit(reindex)
        return jsonify({'status': 'reindexing'}), 200

    # ... existing issue handling ...
```

Enable push events in GitHub App settings, and you're done!

---

## Monitoring Updates

### Check Index Status

```python
from Feature_Components.knowledgeBase import GetIndexStatus

status = GetIndexStatus("owner/repo")
print(f"Last indexed: {status.get('last_modified')}")
print(f"Total functions: {status.get('total_functions')}")
```

### View Index History

```python
from Feature_Components.KnowledgeBase.index_registry import IndexRegistry

registry = IndexRegistry("owner/repo")
indices = registry.list_indices()

for idx in indices:
    print(f"Commit: {idx['commit_sha'][:7]}")
    print(f"Indexed: {idx['indexed_at']}")
    print(f"Functions: {idx['total_functions']}")
    print()
```

---

## Best Practices

1. **Start with Manual**: Test with manual re-indexing first
2. **Monitor Performance**: Track indexing time and resource usage
3. **Set Thresholds**: Re-index fully if > 50 files changed
4. **Handle Errors**: Log failures and alert on repeated errors
5. **Rate Limit**: Don't re-index on every tiny commit
6. **Cache Wisely**: Keep old indices for rollback

---

## Future Enhancements

- [ ] Smart change detection (only re-index affected modules)
- [ ] Parallel indexing for large repositories
- [ ] Delta indices (store only changes)
- [ ] Automatic index pruning (remove old versions)
- [ ] Real-time index updates (< 1 second)
- [ ] Multi-repository batch updates

---

## Summary

**Current State**: Manual re-indexing required after code changes

**Recommended Solution**: Implement automatic push event handling (Option 2)

**Quick Fix**: Add simple re-index on push (5-minute implementation)

**Long-term**: Full incremental indexing with smart change detection

The foundation is there - you just need to connect the push webhook to trigger the incremental indexer! 🚀
