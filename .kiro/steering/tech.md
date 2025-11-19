# SPRINT Technical Stack

## Core Framework

- **Flask** - Python web framework for handling GitHub webhooks
- **Python 3.x** - Primary programming language

## Knowledge Base System

- **tree-sitter** - Code parsing for Python and Java
- **FAISS** - CPU-based vector similarity search
- **Neo4j** - Graph database for code relationships
- **NumPy** - Numerical operations for vector embeddings

## Key Dependencies

- **Requests** - HTTP client for GitHub API calls
- **aiohttp** - Async HTTP client for KB system
- **PyJWT** - GitHub App authentication
- **python-dotenv** - Environment configuration

## Infrastructure

- **ngrok** - Secure tunneling for local development
- **SQLite** - Local database for issue storage
- **GitHub API** - Repository integration and webhook handling

## Hardware Requirements

- **GPU**: Not required (KB system uses CPU-based vector search)
- **Storage**: ~1-2GB for Knowledge Base indices per repository
- **Memory**: 8GB RAM recommended (scales with repository size)

## Common Commands

### Setup and Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env file with GitHub App credentials
# No model downloads required - KB system builds indices automatically
```

### Running the Application

```bash
# Terminal 1: Start ngrok tunnel
ngrok http 5000

# Terminal 2: Start Flask application
python main.py
# or
python -m main
```

### Environment Configuration

Required `.env` variables:

- `GITHUB_PRIVATE_KEY` - GitHub App private key
- `GITHUB_APP_ID` - GitHub App ID
- `CLIENT_ID` - GitHub App client ID
- `POOL_PROCESSOR_MAX_WORKERS` - ThreadPool worker count (default: 4)

## Development Notes

- ThreadPoolExecutor for concurrent webhook processing
- Knowledge Base automatically indexes repositories on installation
- Push events trigger automatic KB updates
- Lightweight CPU-based architecture (no GPU required)
