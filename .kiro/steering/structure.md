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

The main application follows a modular component-based architecture:

```
SPRINT Tool/
├── main.py                    # Flask application entry point
├── requirements.txt           # Python dependencies
├── .env                      # Environment configuration
├── ngrok.exe                 # Tunneling executable
├── Data_Storage/             # Database operations
│   └── dbOperations.py       # SQLite database management
├── Feature_Components/       # Core ML feature implementations
│   ├── dupBRDetection.py     # Duplicate issue detection
│   ├── BRSeverityPred.py     # Severity prediction
│   └── bugLocalization.py   # Bug localization
├── GitHub_Event_Handler/     # GitHub integration layer
│   ├── processIssueEvents.py    # Main event processing logic
│   ├── app_authentication.py   # GitHub App authentication
│   ├── createComment.py        # Issue comment creation
│   ├── createCommentBugLocalization.py  # Bug localization comments
│   └── getCodeFiles.py         # Repository file fetching
└── Issue_Indexer/           # Issue data management
    └── getAllIssues.py      # Repository issue fetching and indexing
```

## Component Responsibilities

### Data_Storage

- Database table creation and management
- Issue data persistence and retrieval
- Repository-specific data isolation

### Feature_Components

- **dupBRDetection.py**: Implements `DuplicateDetection()` API
- **BRSeverityPred.py**: Implements `SeverityPrediction()` API
- **bugLocalization.py**: Implements `BugLocalization()` API
- Each component is self-contained with model loading and inference logic

### GitHub_Event_Handler

- **processIssueEvents.py**: Orchestrates the entire workflow
- **app_authentication.py**: Manages GitHub App credentials and tokens
- **createComment.py**: Handles standard issue comments
- **createCommentBugLocalization.py**: Specialized bug localization output
- **getCodeFiles.py**: Repository file system traversal

### Issue_Indexer

- Fetches existing repository issues during installation
- Implements pagination for large repositories
- Maintains local issue database for similarity comparison

## Key Design Patterns

### Modular Feature Architecture

- Each ML feature is implemented as an independent component
- Features expose simple function-based APIs
- Easy to add new features by following existing patterns

### Event-Driven Processing

- GitHub webhooks trigger issue processing
- ThreadPoolExecutor enables concurrent processing
- Multiprocessing support for ML model inference

### Configuration-Based Models

- All model paths defined in `.env` file
- Support for custom model replacement
- Environment-specific configuration management

## File Naming Conventions

- Snake_case for directories and Python files
- Descriptive component names (e.g., `processIssueEvents.py`)
- Feature-specific prefixes (e.g., `dupBRDetection.py` for duplicate detection)

## Extension Points

- Add new features in `Feature_Components/`
- Integrate new features in `processIssueEvents.py`
- Update environment configuration for new models
- Follow existing API patterns for consistency
