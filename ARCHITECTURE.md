# SPRINT Multi-Language Knowledge Base - Architecture

## System Overview

SPRINT (iSsue rePoRt assIstaNT) is a GitHub application that provides automated bug localization for software repositories using machine learning and semantic code search. The system now supports multiple programming languages (Python and Java) with an extensible architecture for adding more languages.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Webhook                               │
│                    (New Issue Created Event)                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SPRINT Event Handler                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Duplicate   │  │  Severity    │  │  Bug Localization        │  │
│  │  Detection   │  │  Prediction  │  │  (Knowledge Base)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Knowledge Base System (Multi-Language)                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                  Language Detection                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │    │
│  │  │ .py → Python │  │ .java → Java │  │ .js → Future │     │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                  Parser Factory                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │    │
│  │  │ PythonParser │  │  JavaParser  │  │ Future Parser│     │    │
│  │  │ tree-sitter  │  │ tree-sitter  │  │              │     │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │              Code Analysis & Extraction                     │    │
│  │  • Methods/Functions    • Classes/Interfaces                │    │
│  │  • Docstrings/Javadoc   • Call Relationships                │    │
│  │  • Import Statements    • Line Numbers                      │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                  Embedding Generation                       │    │
│  │              (UniXcoder / GraphCodeBERT)                    │    │
│  │         Language-Agnostic Code Embeddings                   │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    Storage Layer                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │    │
│  │  │ FAISS Vector │  │  Neo4j Graph │  │   Metadata   │     │    │
│  │  │    Store     │  │    Store     │  │     JSON     │     │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Bug Localization Pipeline                         │
│                                                                      │
│  Issue Text → Issue Processor → Embedding                           │
│                                     │                                │
│                                     ▼                                │
│                          Dense Retriever (FAISS)                     │
│                                     │                                │
│                                     ▼                                │
│                          Top-K Similar Functions                     │
│                                     │                                │
│                                     ▼                                │
│                          Confidence Calibration                      │
│                                     │                                │
│                                     ▼                                │
│                          Result Formatter                            │
│                                     │                                │
│                                     ▼                                │
│                    Language-Aware Comment Generator                  │
│                                     │                                │
│                                     ▼                                │
│                          GitHub Comment Posted                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Language Parser Layer

```
┌─────────────────────────────────────────────────────────────┐
│                    LanguageParser (Abstract)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  • parse_file()                                      │    │
│  │  • extract_functions()                               │    │
│  │  • extract_classes()                                 │    │
│  │  • extract_imports()                                 │    │
│  │  • extract_calls()                                   │    │
│  │  • get_language_name()                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    PythonParser          │  │     JavaParser           │
│  ┌────────────────────┐  │  │  ┌────────────────────┐  │
│  │ tree-sitter-python │  │  │  │ tree-sitter-java   │  │
│  │                    │  │  │  │                    │  │
│  │ • Functions        │  │  │  │ • Methods          │  │
│  │ • Classes          │  │  │  │ • Classes          │  │
│  │ • Docstrings       │  │  │  │ • Interfaces       │  │
│  │ • Imports          │  │  │  │ • Enums            │  │
│  │ • Calls            │  │  │  │ • Javadoc          │  │
│  └────────────────────┘  │  │  │ • Imports          │  │
│                          │  │  │ • Method Calls     │  │
│  Language: "python"      │  │  └────────────────────┘  │
│  Extensions: [.py]       │  │                          │
│                          │  │  Language: "java"        │
│                          │  │  Extensions: [.java]     │
└──────────────────────────┘  └──────────────────────────┘
```

### 2. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INDEXING PHASE                            │
└─────────────────────────────────────────────────────────────┘

Repository Files
      │
      ▼
┌─────────────────┐
│ File Discovery  │  → Collect all .py and .java files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Language Detect │  → Identify language by extension
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parser Select   │  → Get appropriate parser
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Code Parsing    │  → Extract functions, classes, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding Gen   │  → Generate 768-dim vectors
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ FAISS Index │   │  Neo4j DB   │   │  Metadata   │
│  (Vectors)  │   │  (Graph)    │   │   (JSON)    │
└─────────────┘   └─────────────┘   └─────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   RETRIEVAL PHASE                            │
└─────────────────────────────────────────────────────────────┘

GitHub Issue
      │
      ▼
┌─────────────────┐
│ Issue Process   │  → Clean text, extract keywords
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding Gen   │  → Generate issue embedding
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FAISS Search    │  → Find top-K similar functions
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Confidence Cal  │  → Calibrate scores
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Format Results  │  → Language-aware formatting
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Comment│  → Markdown with syntax highlighting
└────────┬────────┘
         │
         ▼
GitHub Comment Posted
```

### 3. Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FAISS Vector Store                        │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Index: IndexFlatIP (Inner Product)                │     │
│  │  Dimension: 768                                     │     │
│  │  Vectors: [func1_embedding, func2_embedding, ...]  │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Metadata Store (JSON)                     │
│  {                                                           │
│    "repo": "owner/repo",                                     │
│    "commit_sha": "abc123...",                                │
│    "languages": {"python": 150, "java": 200},                │
│    "functions": [                                            │
│      {                                                       │
│        "index": 0,                                           │
│        "id": "func_hash",                                    │
│        "name": "processData",                                │
│        "file_path": "src/Processor.java",                    │
│        "language": "java",                                   │
│        "start_line": 45,                                     │
│        "end_line": 78,                                       │
│        "signature": "public Map<String, Object> ...",        │
│        "docstring": "Process input data..."                  │
│      }                                                       │
│    ]                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Neo4j Graph Store                         │
│                                                              │
│  (File:Python) ──CONTAINS──> (Class:GameEngine)             │
│       │                              │                       │
│       │                              │                       │
│       └──CONTAINS──> (Function:init)                        │
│                              │                               │
│                              └──CALLS──> (Function:setup)   │
│                                                              │
│  (File:Java) ──CONTAINS──> (Class:Processor)                │
│       │                            │                         │
│       │                            │                         │
│       └──CONTAINS──> (Method:processData)                   │
│                            │                                 │
│                            └──CALLS──> (Method:validate)    │
│                                                              │
│  Properties:                                                 │
│    - language: "python" | "java"                             │
│    - file_path: relative path                               │
│    - start_line, end_line: line numbers                     │
│    - signature: method/function signature                   │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Language Support Architecture

### Language Detection Flow

```
File: "Processor.java"
      │
      ▼
┌─────────────────┐
│ Get Extension   │  → ".java"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extension Map   │  → {".py": "python", ".java": "java"}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Language Found  │  → "java"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Get Parser      │  → JavaParser instance
└─────────────────┘
```

### Parser Factory Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    ParserFactory                             │
│                                                              │
│  _parsers = {                                                │
│    "python": PythonParser,                                   │
│    "java": JavaParser                                        │
│  }                                                           │
│                                                              │
│  _extension_map = {                                          │
│    ".py": "python",                                          │
│    ".java": "java"                                           │
│  }                                                           │
│                                                              │
│  Methods:                                                    │
│  • register_parser(lang, parser_class, extensions)          │
│  • get_parser(file_path) → LanguageParser                   │
│  • get_supported_languages() → List[str]                    │
│  • get_supported_extensions() → List[str]                   │
└─────────────────────────────────────────────────────────────┘
```

## GitHub Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub App Setup                          │
│                                                              │
│  1. GitHub App Created                                       │
│  2. Webhook URL: https://your-server.com/webhook            │
│  3. Events Subscribed: issues (opened, edited)              │
│  4. Permissions: issues (read/write), contents (read)       │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Webhook Handler                           │
│                                                              │
│  POST /webhook                                               │
│    │                                                         │
│    ├─> Verify Signature                                     │
│    ├─> Parse Payload                                        │
│    ├─> Extract Issue Data                                   │
│    └─> Trigger Processing                                   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Issue Processing                          │
│                                                              │
│  1. Clone/Update Repository                                 │
│  2. Check if Indexed (or Index if needed)                   │
│  3. Run Bug Localization                                    │
│  4. Generate Comment                                        │
│  5. Post Comment to GitHub                                  │
│  6. Apply Confidence Label                                  │
└─────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

### Indexing Performance

| Repository Size           | Files  | Functions | Indexing Time | Storage |
| ------------------------- | ------ | --------- | ------------- | ------- |
| Small (< 100 files)       | 50     | 250       | ~30 seconds   | ~5 MB   |
| Medium (100-1000 files)   | 500    | 2,500     | ~5 minutes    | ~50 MB  |
| Large (1000-5000 files)   | 2,500  | 12,500    | ~20 minutes   | ~250 MB |
| Very Large (> 5000 files) | 10,000 | 50,000    | ~60 minutes   | ~1 GB   |

### Retrieval Performance

| Operation              | Latency         | Notes                       |
| ---------------------- | --------------- | --------------------------- |
| Issue Processing       | < 1 second      | Text cleaning and embedding |
| FAISS Search           | < 1 second      | Top-10 retrieval            |
| Confidence Calibration | < 100 ms        | Threshold lookup            |
| Comment Generation     | < 500 ms        | Markdown formatting         |
| **Total End-to-End**   | **< 3 seconds** | From issue to comment       |

## Scalability Considerations

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer                             │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┼────────┬────────┐
    ▼        ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Worker │ │ Worker │ │ Worker │ │ Worker │
│   1    │ │   2    │ │   3    │ │   4    │
└────────┘ └────────┘ └────────┘ └────────┘
    │        │        │        │
    └────────┴────────┴────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐
│ FAISS  │ │ Neo4j  │ │ Redis  │
│ Shared │ │ Shared │ │ Cache  │
└────────┘ └────────┘ └────────┘
```

### Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Cache Layers                              │
│                                                              │
│  L1: Model Cache (In-Memory)                                │
│      • Embedding model loaded once                          │
│      • Reused across requests                               │
│                                                              │
│  L2: Index Cache (In-Memory)                                │
│      • FAISS indices loaded on startup                      │
│      • Metadata cached in memory                            │
│                                                              │
│  L3: Result Cache (Redis - Optional)                        │
│      • Cache recent query results                           │
│      • TTL: 1 hour                                          │
│      • Key: hash(issue_text + repo_name)                    │
└─────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
│                                                              │
│  1. GitHub Webhook Verification                             │
│     • HMAC signature validation                             │
│     • Reject unsigned requests                              │
│                                                              │
│  2. GitHub App Authentication                               │
│     • JWT token generation                                  │
│     • Installation access tokens                            │
│     • Scoped permissions                                    │
│                                                              │
│  3. Repository Access Control                               │
│     • Only process installed repositories                   │
│     • Respect GitHub permissions                            │
│                                                              │
│  4. Data Privacy                                            │
│     • Code stored locally only                              │
│     • Embeddings are anonymized                             │
│     • No PII in logs                                        │
│                                                              │
│  5. Rate Limiting                                           │
│     • GitHub API rate limits respected                      │
│     • Internal rate limiting per repository                 │
└─────────────────────────────────────────────────────────────┘
```

## Extension Points

### Adding a New Language

```
1. Install tree-sitter grammar
   pip install tree-sitter-javascript

2. Create Parser Class
   class JavaScriptParser(LanguageParser):
       def __init__(self):
           self.language = Language(tsjavascript.language(), "javascript")
           self.parser = Parser()
           self.parser.set_language(self.language)

       # Implement abstract methods...

3. Register in ParserFactory
   # In parser_factory.py
   self.register_parser("javascript", JavaScriptParser, [".js", ".jsx"])

4. Update Configuration
   # In config.py
   SUPPORTED_LANGUAGES['javascript'] = {
       'extensions': ['.js', '.jsx'],
       'parser': 'JavaScriptParser',
       'syntax_highlight': 'javascript'
   }

5. Add Tests
   # Create test_javascript_parser.py
```

## Monitoring and Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    Telemetry System                          │
│                                                              │
│  Metrics Tracked:                                            │
│  • Indexing time per repository                             │
│  • Retrieval latency per query                              │
│  • Confidence distribution                                   │
│  • Language usage statistics                                │
│  • Error rates by component                                 │
│  • Cache hit rates                                          │
│                                                              │
│  Logging:                                                    │
│  • Structured JSON logs                                     │
│  • Log levels: DEBUG, INFO, WARNING, ERROR                  │
│  • Correlation IDs for request tracing                      │
│                                                              │
│  Alerts:                                                     │
│  • High error rate (> 5%)                                   │
│  • Slow queries (> 10 seconds)                              │
│  • Index failures                                           │
│  • GitHub API rate limit approaching                        │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component      | Technology         | Version | Purpose             |
| -------------- | ------------------ | ------- | ------------------- |
| Language       | Python             | 3.8+    | Core implementation |
| Web Framework  | Flask              | 3.0+    | Webhook handling    |
| ML Framework   | PyTorch            | 2.0+    | Model inference     |
| Embeddings     | Transformers       | 4.0+    | Code embeddings     |
| Vector Search  | FAISS              | 1.8+    | Similarity search   |
| Graph Database | Neo4j              | 5.0+    | Code relationships  |
| Code Parsing   | tree-sitter        | 0.21+   | AST parsing         |
| Python Grammar | tree-sitter-python | 0.21.0  | Python parsing      |
| Java Grammar   | tree-sitter-java   | 0.21.0  | Java parsing        |

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Deployment                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Reverse Proxy (Nginx)                             │     │
│  │  • SSL Termination                                 │     │
│  │  • Load Balancing                                  │     │
│  └────────────────┬───────────────────────────────────┘     │
│                   │                                          │
│  ┌────────────────┴───────────────────────────────────┐     │
│  │  Application Server (Gunicorn)                     │     │
│  │  • Multiple workers                                │     │
│  │  • Process management                              │     │
│  └────────────────┬───────────────────────────────────┘     │
│                   │                                          │
│  ┌────────────────┴───────────────────────────────────┐     │
│  │  Flask Application                                 │     │
│  │  • Webhook handling                                │     │
│  │  • Request routing                                 │     │
│  └────────────────┬───────────────────────────────────┘     │
│                   │                                          │
│  ┌────────────────┴───────────────────────────────────┐     │
│  │  Knowledge Base System                             │     │
│  │  • Multi-language support                          │     │
│  │  • Bug localization                                │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```
