# SPRINT Project Structure

## Root Directory Layout

```
├── assets/                     # Documentation images and logos
├── Replication Package/        # Research materials and evaluation data
│   ├── Evaluation/            # Model training and evaluation scripts
│   ├── SPRINT Test Cases/     # Test cases for the three features
│   └── User Study/            # User study questionnaire and results
└── SPRINT Tool/               # Main application codebase
```

## SPRINT Tool Architecture

The main application follows a simplified, focused architecture:

```
SPRINT Tool/
├── main.py                    # Flask application entry point
├── requirements.txt           # Python dependencies
├── .env                      # Environment configuration
├── ngrok.exe                 # Tunneling executable
├── Data_Storage/             # Database operations
│   └── dbOperations.py       # SQLite database management
├── Feature_Components/       # Knowledge Base bug localization
│   ├── knowledgeBase.py      # KB-based bug localization
│   └── KnowledgeBase/        # KB system implementation
├── GitHub_Event_Handler/     # GitHub integration layer
│   ├── processIssueEvents.py    # Main event processing logic
│   ├── app_authentication.py   # GitHub App authentication
│   ├── createCommentBugLocalization.py  # Bug localization comments
│   ├── getCodeFiles.py         # Repository file fetching
│   └── processPushEvents.py    # Push event handling for KB updates
└── Issue_Indexer/           # Issue data management
    └── getAllIssues.py      # Repository issue fetching and indexing
```

## Component Responsibilities

### Data_Storage

- Database table creation and management
- Issue data persistence and retrieval
- Repository-specific data isolation

### Feature_Components

- **knowledgeBase.py**: Implements Knowledge Base bug localization using vector similarity search
- **KnowledgeBase/**: Contains the KB system implementation with code parsing, indexing, and retrieval

### GitHub_Event_Handler

- **processIssueEvents.py**: Orchestrates the bug localization workflow
- **app_authentication.py**: Manages GitHub App credentials and tokens
- **createCommentBugLocalization.py**: Creates bug localization comments
- **getCodeFiles.py**: Repository file system traversal
- **processPushEvents.py**: Handles push events to update Knowledge Base

### Issue_Indexer

- Fetches existing repository issues during installation
- Implements pagination for large repositories
- Maintains local issue database

## Key Design Patterns

### Focused Single-Feature Architecture

- Knowledge Base bug localization is the core feature
- Simple function-based API for bug localization
- Lightweight and efficient implementation

### Event-Driven Processing

- GitHub webhooks trigger issue processing
- ThreadPoolExecutor enables concurrent processing
- Push events trigger automatic Knowledge Base updates

### Knowledge Base System

- Vector similarity search using FAISS
- Code parsing with tree-sitter
- Graph database (Neo4j) for code relationships
- Automatic indexing on repository installation

## File Naming Conventions

- Snake_case for directories and Python files
- Descriptive component names (e.g., `processIssueEvents.py`)
- Clear separation between event handling and feature logic

## Extension Points

- Enhance Knowledge Base system with additional language support
- Improve vector search algorithms
- Add more sophisticated code analysis features
- Extend telemetry and monitoring capabilities
