# INSIGHT Multi-Language Knowledge Base - Usage Manual

## Table of Contents

1. [Quick Start](#quick-start)
2. [Testing with Local Repositories](#testing-with-local-repositories)
3. [GitHub Plugin Setup](#github-plugin-setup)
4. [Python Repository Testing](#python-repository-testing)
5. [Java Repository Testing](#java-repository-testing)
6. [Mixed-Language Repository Testing](#mixed-language-repository-testing)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Quick Start

### Prerequisites

```bash
# Python 3.11 or higher
python --version

# Git
git --version

# Neo4j (Required for GraphRAG features)
# Download from: https://neo4j.com/download/

# Google Gemini API Key
# Get one from: https://aistudio.google.com/app/apikey
```

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd issue_analyzing_tool

# 2. Install dependencies
cd "INSIGHT Tool"
pip install -r requirements.txt

# 3. Verify installation
python -c "from Feature_Components.knowledgeBase import IndexRepository; print('✓ Installation successful')"
```

---

## Testing with Local Repositories

### Test Script Setup

Create a test script to index and query repositories:

```python
# test_repository.py
import sys
import os

# Add INSIGHT Tool to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'INSIGHT Tool'))

from Feature_Components.knowledgeBase import IndexRepository, BugLocalization

# Index a repository
result = IndexRepository(
    repo_path="path/to/your/repository",
    repo_name="owner/repo-name",
    model_name="microsoft/unixcoder-base"
)

print(f"Indexed {result['total_functions']} functions from {result['total_files']} files")

# Test bug localization
results = BugLocalization(
    issue_title="Bug in data processing",
    issue_body="The process_data function crashes when input is empty",
    repo_owner="owner",
    repo_name="repo-name",
    repo_path="path/to/your/repository",
    k=10
)

print(f"Found {results.get('total_results', 0)} relevant functions")
if 'top_files' in results:
    for file_data in results['top_files'][:3]:
        print(f"  - {file_data['file_path']}: {len(file_data['functions'])} functions")
```

---

## Python Repository Testing

### Step 1: Prepare Python Repository

```bash
# Example: Test with a Python project
git clone https://github.com/example/python-project
cd python-project
```

### Step 2: Index the Repository

```python
# index_python_repo.py
import sys
sys.path.insert(0, '../INSIGHT Tool')

from Feature_Components.knowledgeBase import IndexRepository

result = IndexRepository(
    repo_path="python-project",
    repo_name="example/python-project",
    model_name="microsoft/unixcoder-base"
)

print(f"""
Indexing Complete!
==================
Files indexed: {result['total_files']}
Functions found: {result['total_functions']}
Commit SHA: {result['commit_sha']}
Index path: {result['index_path']}
Time taken: {result['indexing_time_seconds']:.2f} seconds
""")
```

### Step 3: Test Bug Localization

```python
# test_python_bug.py
import sys
sys.path.insert(0, '../INSIGHT Tool')

from Feature_Components.knowledgeBase import BugLocalization

# Example: Find bug in authentication module
results = BugLocalization(
    issue_title="Authentication fails for new users",
    issue_body="""
    When a new user tries to register, the authentication system
    throws an error. The validate_user function seems to be checking
    for existing users incorrectly. The login method also has issues
    with password hashing.
    """,
    repo_owner="example",
    repo_name="python-project",
    repo_path="python-project",
    k=10,
    enable_line_level=True
)

# Display results
print(f"\nBug Localization Results")
print(f"========================")
print(f"Confidence: {results.get('confidence_level', 'unknown')} ({results.get('confidence_score', 0):.0%})")

print(f"\nLLM Analysis:")
print(results.get('llm_analysis', 'No analysis available'))

print(f"\nTop 5 Candidate Functions:")
rank = 1
if 'top_files' in results:
    for file_data in results['top_files'][:5]:
        for func in file_data['functions'][:2]:
            print(f"\n{rank}. {func['name']} in {file_data['file_path']}")
            print(f"   Language: {func.get('language', 'python')}")
            print(f"   Score: {func['score']:.3f}")
            print(f"   Lines: {func['line_range'][0]}-{func['line_range'][1]}")
            rank += 1
            if rank > 5:
                break
```

### Expected Output

```
Bug Localization Results
========================
Confidence: high (92%)

LLM Analysis:
The issue appears to be in the user validation logic. The `validate_user` function checks for existing users but fails to handle the case where the database connection is null...

Top 5 Candidate Functions:

1. validate_user in auth/validator.py
   Language: python
   Score: 0.945
   Lines: 45-78

2. login in auth/authentication.py
   Language: python
   Score: 0.887
   Lines: 120-145
```

---

## GitHub Plugin Setup

### Step 1: Create GitHub App

1. Go to GitHub Settings → Developer settings → GitHub Apps
2. Click "New GitHub App"
3. Fill in the details:

   - **Name**: INSIGHT Bug Localization
   - **Homepage URL**: Your server URL
   - **Webhook URL**: `https://your-server.com/webhook`
   - **Webhook Secret**: Generate a secure secret

4. Set Permissions:

   - **Issues**: Read & Write
   - **Contents**: Read only
   - **Metadata**: Read only

5. Subscribe to Events:

   - ☑ Issues (opened, edited)
   - ☑ Installation (created, deleted)

6. Click "Create GitHub App"

### Step 2: Configure Environment

```bash
# Create .env file in INSIGHT Tool directory
cat > "INSIGHT Tool/.env" << EOF
# GitHub App Configuration
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY=path/to/private-key.pem
CLIENT_ID=your_client_id
WEBHOOK_SECRET=your_webhook_secret

# LLM Configuration (Gemini)
GEMINI_API_KEY=your_gemini_api_key
LLM_MODEL_NAME=gemini-2.0-flash
LLM_TEMPERATURE=0.2

# Model Paths
DUPLICATE_BR_MODEL_PATH=path/to/duplicate_model
SEVERITY_PREDICTION_MODEL_PATH=path/to/severity_model
BUGLOCALIZATION_MODEL_PATH=path/to/buglocalization_model

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Performance
POOL_PROCESSOR_MAX_WORKERS=4
EOF
```

### Step 3: Start the Server

```bash
# Terminal 1: Start ngrok (for local testing)
ngrok http 5000

# Terminal 2: Start Flask application
cd "INSIGHT Tool"
python main.py
```

### Step 4: Install on Repository

1. Go to your GitHub App settings
2. Click "Install App"
3. Select repositories to install on
4. Authorize the installation

### Step 5: Test the Integration

1. Create a new issue in your repository:

```markdown
Title: Bug in user authentication

Body:
The login function is not working correctly. When users try to log in
with valid credentials, they get an authentication error. The validate_password
method seems to be comparing hashes incorrectly.
```

2. Wait for INSIGHT to process (usually < 15 seconds)

3. Check for the automated comment:

````markdown
## 🔍 Bug Localization Results

**Confidence:** High (92% probability) 🟢

### 🧠 Technical Analysis
The issue stems from an incorrect hash comparison in `validate_password`. The function uses `==` instead of `bcrypt.checkpw`, which causes the comparison to fail even for valid passwords...

### 🧪 Hypothesis
The `validate_password` function in `auth/validator.py` is implementing a direct string comparison for password hashes, which is incorrect and insecure. It should use the library's verification method.

### 🛠️ Suggested Patch
```python
def validate_password(input_password, stored_hash):
-    return input_password == stored_hash
+    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hash)
```

### Top Candidate Functions

#### 1. `validate_password` in `auth/validator.py` (Score: 0.92)
**Lines 45-67** | [View on GitHub](...)
````

---

## API Reference

### IndexRepository

Index a repository for bug localization.

```python
from Feature_Components.knowledgeBase import IndexRepository

result = IndexRepository(
    repo_path: str,              # Path to repository root
    repo_name: str,              # Repository name (e.g., "owner/repo")
    model_name: str = "microsoft/unixcoder-base",  # Embedding model
    neo4j_uri: str = "bolt://localhost:7687",      # Neo4j URI
    neo4j_user: str = "neo4j",                     # Neo4j username
    neo4j_password: str = "password"               # Neo4j password
)
```

### BugLocalization

Perform bug localization on a GitHub issue.

```python
from Feature_Components.knowledgeBase import BugLocalization

results = BugLocalization(
    issue_title: str,            # GitHub issue title
    issue_body: str,             # GitHub issue body text
    repo_owner: str,             # Repository owner
    repo_name: str,              # Repository name
    repo_path: str,              # Local path to repository
    commit_sha: str = None,      # Specific commit (optional)
    k: int = 10,                 # Number of top results
    enable_line_level: bool = True  # Enable line-level localization
)

# Returns:
{
    'repository': 'owner/repo',
    'confidence_level': 'high',
    'confidence_score': 0.92,
    'llm_analysis': '...',
    'llm_hypothesis': '...',
    'llm_patch': '...',
    'top_files': [
        {
            'file_path': 'src/module.py',
            'score': 0.87,
            'functions': [
                {
                    'name': 'process_data',
                    'line_range': [45, 78],
                    'score': 0.87,
                    # ...
                }
            ]
        }
    ]
}
```

---

## Troubleshooting

### Common Issues

#### 1. "LLM Analysis Failed"

**Problem**: Missing or invalid Gemini API key.

**Solution**:
Check your `.env` file and ensure `GEMINI_API_KEY` is set correctly.

#### 2. "Repository not indexed"

**Problem**: Trying to localize bugs in an unindexed repository.

**Solution**:
Ensure the repository is installed via the GitHub App or manually indexed using `IndexRepository`.

#### 3. "Failed to connect to Neo4j"

**Problem**: Neo4j database not running.

**Solution**:
Start Neo4j (`neo4j start`) and check connection settings in `.env`.

#### 4. "Lines 0-0" in Results

**Problem**: Line number metadata missing from index.

**Solution**:
Re-index the repository to capture line numbers correctly.

### Performance Issues

If indexing is slow:
1.  **Use GPU**: Install PyTorch with CUDA support.
2.  **Check Neo4j**: Ensure Neo4j has enough memory allocated.
