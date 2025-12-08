# INSIGHT - Automated Bug Localization

## System Overview

INSIGHT (Issue Analyzing Tool) is a GitHub application that provides automated bug localization and technical analysis using a **RAG (Retrieval-Augmented Generation)** pipeline. It combines semantic search with LLM-powered analysis to identify buggy code and suggest fixes.

**Key Features:**
- **RAG-based Localization**: Dense vector retrieval + LLM re-ranking
- **Smart Query Generation**: LLM generates optimized search queries
- **Graph Enrichment**: Adds caller/callee context from code knowledge graph
- **Multi-Language Support**: Python, Java, Kotlin
- **GitHub Integration**: Automated knowledge base updates on code changes

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    GitHub Webhooks                        │
│         ┌──────────────┬──────────────┐                   │
│         │Issue Events  │Push Events   │                   │
│         └──────┬───────┴───────┬──────┘                   │
│                │               │                          │
│                ▼               ▼                          │
│       ┌────────────┐  ┌────────────────┐                 │
│       │Issue       │  │Repository      │                 │
│       │Handler     │  │Indexer         │                 │
│       └──────┬─────┘  └────────┬───────┘                 │
│              │                 │                          │
│              │                 ▼                          │
│              │        ┌────────────────┐                  │
│              │        │Knowledge Base  │                  │
│              │        │• FAISS (Vectors)│                  │
│              │        │• Neo4j (Graph)  │                  │
│              │        └────────┬───────┘                  │
│              │                 │                          │
│              ▼                 │                          │
│       ┌───────────────────────▼──────┐                   │
│       │    Bug Localization Pipeline  │                  │
│       │    (BugLocalization class)    │                  │
│       │                               │                  │
│       │  1. Generate Search Query     │                  │
│       │     (LLM)                     │                  │
│       │  2. Dense Retrieval           │                  │
│       │     (FAISS, k=20)             │                  │
│       │  3. Graph Enrichment          │                  │
│       │     (Neo4j: callers/callees)  │                  │
│       │  4. LLM Selection             │                  │
│       │     (Top 5 entities)          │                  │
│       │  5. Generate Analysis &Patch  │                  │
│       │     (LLM)                     │                  │
│       └───────────────────────────────┘                  │
│                       │                                   │
│                       ▼                                   │
│              GitHub Comment Posted                        │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Bug Localization Pipeline (`bug_localization.py`)
The core RAG retrieval pipeline for candidate identification:

1. **Issue Processing**: Preprocesses issue title and body
2. **Query Generation**: LLM generates semantic search query from issue
3. **Dense Retrieval**: Retrieves top-k candidate entities (Files, Classes, and Functions) using UnixCoder embeddings
4. **Graph Enrichment**: Adds callers/callees context from Neo4j and consistently ensures parent context (e.g., File for a Function)
5. **LLM Selection**: GPT-4o/Gemini selects top-n most likely buggy entities with reasoning
6. **Return**: Returns ranked list of candidates (top-selected entities + remaining candidates)

### 2. Knowledge Base Components

#### Vector Store (`retriever.py` + FAISS)
- Stores embeddings of all Files, Classes, and Functions in the repository
- Uses Microsoft's UnixCoder model
- Enables semantic similarity search

#### Graph Store (`graph_store.py` + Neo4j)
- Stores code structure: Files, Classes, Functions, Calls
- Provides caller/callee relationships
- Enables graph-based context enrichment

#### Repository Indexer (`indexer.py`)
- Parses Python/Java/Kotlin code using tree-sitter
- Extracts functions and their relationships
- Generates embeddings and stores in FAISS
- Builds knowledge graph in Neo4j

### 3. LLM Service (`llm_service.py`)
Provides LLM capabilities:
- **Query Generation**: Creates optimized search queries
- **Function Selection**: Identifies root cause entities (Files, Classes, Functions)
- **Analysis**: Explains the bug
- **Patch Generation**: Suggests fixes

Supports: GPT-4o, Gemini 2.0 Flash

### 4. Workflow Manager (`workflow_manager.py`)
LangGraph-based orchestration (main flow for GitHub app):
- Orchestrates full bug localization workflow in 3 steps
- Step 1: Calls `BugLocalization` for candidate retrieval and selection
- Step 2: Extracts analysis/reasoning from LLM-selected functions
- Step 3: Generates patch suggestions using LLM
- Returns complete results with localization, analysis, and patches

**Note**: The GitHub integration uses `WorkflowManager` via the `BugLocalization()` API function in `knowledgeBase.py`.

## Data Flow

### Indexing Phase
```
Repository → Parse (tree-sitter) → Extract Files, Classes, Functions →
  ├─ Generate Embeddings (UnixCoder) → FAISS
  └─ Build Graph (relationships) → Neo4j
```

### Localization Phase
```
GitHub Issue →
  1. Generate Search Query (LLM) →
  2. Embed Query (UnixCoder) →
  3. Retrieve Candidates (FAISS, k=20) →
  4. Enrich with Graph Context (Neo4j) →
  5. LLM Selection (Top 5) →
  6. Analysis & Patch (LLM) →
GitHub Comment
```

## Technology Stack

| Component | Technology | Purpose |
|:---|:---|:---|
| **Language** | Python 3.11+ | Core implementation |
| **LLM** | GPT-4o / Gemini 2.0 | Reasoning and generation |
| **Embeddings** | UnixCoder | Code embeddings |
| **Vector Search** | FAISS | Similarity search |
| **Graph DB** | Neo4j | Knowledge graph |
| **Parsing** | tree-sitter | AST extraction |
| **Orchestration** | LangGraph | Workflow management |
| **Web Framework** | Flask | Webhook handling |

## Evaluation Results

On the [LCA Bug Localization benchmark](https://huggingface.co/datasets/JetBrains-Research/lca-bug-localization):

**File-Level Metrics (k=3)**:
- Hit@3: **76.67%**
- Precision@3: **35.56%**
- Recall@3: **50.06%**
- F1@3: **38.47%**

**Function-Level Metrics (k=3)**:
- Hit@3: **13.33%**
- F1@3: **5.24%**

## Storage

- **SQLite**: Repository metadata, indexing status
- **FAISS**: Embeddings for Files, Classes, and Functions (one index per repository)
- **Neo4j**: Code knowledge graph (shared across repositories)
- **Local Files**: Cloned repositories (temporary)
