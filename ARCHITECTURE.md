# INSIGHT Multi-Language Knowledge Base - Architecture

## System Overview

INSIGHT (Issue Analyzing Tool) is a GitHub application that provides automated bug localization and technical analysis for software repositories. It leverages an **Agentic RAG (Retrieval-Augmented Generation)** architecture, combining graph-based retrieval (GraphRAG) with Large Language Models (LLMs) to understand code context and suggest fixes.

**Key Features:**

- **Agentic Workflow**: Uses LangGraph to orchestrate a multi-step reasoning process (Retrieve -> Analyze -> Hypothesize -> Patch).
- **GraphRAG**: Combines vector similarity search with knowledge graph traversals and directory summarization for rich context.
- **LLM Integration**: Powered by Google Gemini 2.0 Flash for deep code analysis and patch generation.
- **Multi-Language Support**: Python and Java with extensible architecture.
- **Automatic Knowledge Base Updates**: Automatically updates code indices when developers push changes.
- **Production-Ready**: Comprehensive error handling, metrics tracking, and monitoring.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Webhooks                              │
│         ┌──────────────────────┬──────────────────────┐             │
│         │  Issue Events        │   Push Events        │             │
│         │  (opened, edited)    │   (code changes)     │             │
│         └─────────┬────────────┴──────────┬───────────┘             │
│                   │                       │                         │
│                   ▼                       ▼                         │
┌─────────────────────┐  ┌─────────────────────────────────────┐      │
│  Issue Event        │  │  Push Event Handler                 │      │
│  Handler            │  │  • Repository Sync                  │      │
│                     │  │  • Change Detection                 │      │
│  ┌──────────────┐  │  │  • Incremental Update               │      │
│  │  Duplicate   │  │  │  • Metrics Tracking                 │      │
│  │  Detection   │  │  └─────────────────────────────────────┘      │
│  └──────────────┘  │           │                                    │
│           │        │           ▼                                    │
│           │        │  ┌─────────────────────────────────────┐      │
│           │        │  │  Update Strategy Decision           │      │
│           │        │  │  ├─ Initial: Full index             │      │
│           │        │  │  ├─ Incremental: Changed files      │      │
│           │        │  │  └─ Full: Complete reindex          │      │
│           │        │  └─────────────────────────────────────┘      │
│           │        │           │                                    │
│           ▼        └───────────┼────────────────────────────────────┘
│                                ▼
│  ┌────────────────────────────────────────────────────────────┐
│  │              Knowledge Base System (Multi-Language)         │
│  │                                                            │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  │  Vector DB   │  │  Graph DB    │  │  LLM Service │    │
│  │  │   (FAISS)    │  │   (Neo4j)    │  │   (Gemini)   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │
│  └────────────────────────────────────────────────────────────┘
│                                │
│                                ▼
│  ┌────────────────────────────────────────────────────────────┐
│  │                 Agentic RAG Workflow (LangGraph)            │
│  │                                                            │
│  │  Start ──> [Process Issue] ──> [Retrieve Context]          │
│  │                                       │                    │
│  │                                       ▼                    │
│  │        [Generate Patch] <── [Analyze Bug & Hypothesize]    │
│  │               │                                            │
│  │               ▼                                            │
│  │        [Format Result] ──> [Post GitHub Comment]           │
│  └────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Knowledge Base Layer

The Knowledge Base is the foundation of the system, storing code structure and semantics.

- **Vector Store (FAISS)**: Stores embeddings of functions and code snippets for semantic similarity search.
- **Graph Store (Neo4j)**: Stores the structural relationships of the code (Files, Classes, Functions, Calls, Imports, Directories).
- **Directory Summaries**: Stores high-level summaries of directory contents to provide architectural context to the LLM.

### 2. Agentic Workflow (LangGraph)

The bug localization process is modeled as a state graph:

1.  **Process Issue**: Cleans and embeds the issue title and body.
2.  **Retrieve Context**:
    *   **Vector Search**: Finds top-k similar functions using FAISS.
    *   **Graph Traversal**: Retrieves call graphs and dependencies for the candidate functions from Neo4j.
    *   **Directory Context**: Fetches summaries of the directories containing the candidate files.
3.  **Analyze Bug**:
    *   Uses Gemini to analyze the issue against the retrieved code context.
    *   Generates a technical analysis and a hypothesis for the bug's location and cause.
4.  **Generate Patch**:
    *   Uses Gemini to suggest a code fix (patch) based on the hypothesis and the specific target file.

### 3. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INDEXING PHASE                            │
└─────────────────────────────────────────────────────────────┘

Repository Files
      │
      ▼
┌─────────────────┐
│ Code Parsing    │  → Extract AST (tree-sitter)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Graph Build     │  → Create Nodes & Edges in Neo4j
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding Gen   │  → Generate Code Embeddings (UniXcoder)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Summarization   │  → Generate Directory Summaries (LLM)
└────────┬────────┘
         │
         ▼
    [Storage]
 (FAISS + Neo4j)

┌─────────────────────────────────────────────────────────────┐
│                   RETRIEVAL & ANALYSIS PHASE                 │
└─────────────────────────────────────────────────────────────┘

GitHub Issue
      │
      ▼
┌─────────────────┐
│ Workflow Start  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Retr.   │  → Vector Search + Graph Traversal
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Analysis    │  → "Explain why this is a bug..."
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Patch Gen       │  → "Suggest a fix..."
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Comment Gen     │  → Format Analysis, Hypothesis, Patch
└────────┬────────┘
         │
         ▼
GitHub Comment Posted
```

## Technology Stack

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | Python | 3.11+ | Core implementation |
| **Orchestration** | LangGraph | 0.2+ | Agentic workflow management |
| **LLM** | Google Gemini | 2.0 Flash | Reasoning and generation |
| **Vector Search** | FAISS | 1.8+ | Similarity search |
| **Graph DB** | Neo4j | 5.0+ | Knowledge graph |
| **Embeddings** | UniXcoder | - | Code embeddings |
| **Parsing** | tree-sitter | 0.21+ | AST parsing |
| **Web Framework** | Flask | 3.0+ | Webhook handling |

## Deployment Architecture

The application is containerized and designed to run in a cloud environment (e.g., AWS, Azure) or locally with ngrok for testing.

- **Flask App**: Handles GitHub webhooks.
- **Worker Process**: Executes the LangGraph workflow (can be async).
- **Neo4j Instance**: Stores the knowledge graph.
- **Local/S3 Storage**: Stores FAISS indices and metadata.

## Monitoring

- **Telemetry**: Tracks indexing time, retrieval latency, and LLM token usage.
- **Logging**: Structured logs for debugging and auditing.
