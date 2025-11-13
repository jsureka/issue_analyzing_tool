"""
Configuration constants for Knowledge Base System
"""

import os
from pathlib import Path

# Model Configuration
DEFAULT_MODEL_NAME = "microsoft/unixcoder-base"
EMBEDDING_DIMENSION = 768
MAX_TOKEN_LENGTH = 512
BATCH_SIZE = 32

# Storage Paths
BASE_DIR = Path(__file__).parent.parent.parent
INDEX_STORAGE_DIR = BASE_DIR / "Data_Storage" / "KnowledgeBase"
INDEX_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Retrieval Configuration
DEFAULT_TOP_K = 10
MAX_TOP_K = 50
MIN_ISSUE_WORDS = 10

# Performance Configuration
MAX_SNIPPET_LENGTH = 500
MAX_FUNCTION_BODY_LENGTH = 2000

# Logging Configuration
LOG_LEVEL = os.getenv("KB_LOG_LEVEL", "INFO")
