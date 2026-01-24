# INSIGHT - Automated Bug Localization Tool

[![GitHub](https://img.shields.io/badge/GitHub-App-blue)](https://github.com/apps/insight-issues)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

INSIGHT is a GitHub application that automatically localizes bugs in software repositories using a RAG (Retrieval-Augmented Generation) pipeline. It analyzes GitHub issues and identifies the specific files and functions that need to be modified to fix the bug.

## Features

✨ **Agentic RAG**: LangGraph-based agent that plans, retrieves, expands, and selects candidates  
🎯 **Smart Query Generation**: Planner node looks at the issue and generates precise search queries  
📊 **Graph-Augmented**: Expander node enriches candidates with 1-hop caller/callee neighbors (Neo4j)  
🧠 **Chain-of-Thought Patching**: Generates fixes using a rigorous 5-step reasoning process (Strategy -> Rationale -> Patch -> Verification -> Quality)  
🌍 **Multi-Language**: Supports Python, Java, and Kotlin  
⚡ **Auto-Updates**: Automatically updates knowledge base when code changes  
📈 **High Accuracy**: 59.52% Hit@3 on LCA benchmark

## How It Works

**1. Agentic Localization (Graph-Based RAG)**
The core localization is handled by a `BugLocalizationAgent` built with **LangGraph**:
1.  **Planner Node**: Analyzes the issue to generate targeted search queries.
2.  **Retriever Node**: Fetches top candidates using **Deep Semantics** (`jina-embeddings-v2-base-code`).
3.  **Expander Node**: Crawls the **Code Knowledge Graph** (Neo4j) to find relevant neighbors (callers/callees) missed by vector search.
4.  **Selector Node**: Uses LLM to rank and select the root cause candidates.

**2. Patch Generation (Chain-of-Thought)**
Once localized, the system generates a fix using a 5-step Chain-of-Thought protocol:
1.  **Define Objective**: Analyze constraints.
2.  **Strategies**: Compare repair approaches (e.g., Guard Clause).
3.  **Design**: Draft the minimal patch.
4.  **Verification**: Simulate bug/normal/edge cases.
5.  **Assessment**: Rate quality and side effects.

**3. Delivery**
- The analysis and JSON-structured patch are posted back to GitHub.

## Quick Start

### Prerequisites

- Python 3.11+
- Neo4j 5.0+
- OpenAI API key or Google API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/issue_analyzing_tool.git
cd issue_analyzing_tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cd "INSIGHT Tool"
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Start Neo4j database

5. Run the application:
```bash
cd "INSIGHT Tool"
python main.py
```

## Configuration

Edit `.env` file in the `INSIGHT Tool` directory:

```env
# LLM Configuration
LLM_MODEL_NAME=gpt-4o  # or gemini-2.0-flash-exp
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# GitHub App (if using)
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=path_to_key.pem
```

## Usage

### As a GitHub App

1. Install the INSIGHT GitHub App on your repository
2. When an issue is created, INSIGHT will automatically:
   - Index the repository (first time only)
   - Analyze the issue
   - Post a comment with localization results

### Standalone Evaluation

Run the evaluation script:

```bash
cd "Replication Package\Evaluation\Bug Localization"
python evaluate_bug_localization.py
```

This will:
- Load test dataset from `test_dataset.xlsx`
- Run bug localization on each issue
- Save results to `evaluation_results_bug_localization.xlsx`

## Evaluation Results

Performance on the [LCA Bug Localization benchmark](https://huggingface.co/datasets/JetBrains-Research/lca-bug-localization) (30 issues, Python/Java/Kotlin):

**File-Level**:
- **Hit@3**: 59.52%
- **Precision@5**: 56.75%
- **Recall@5**: 43.00%
- **F1@5**: 48.93%

**Function-Level**:
- **Hit@3**: 54.76%
- **F1@5**: 42.79%

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture.

**Key Components**:
- `agent.py`: LangGraph-based Agentic RAG pipeline (Planner -> Retriever -> Expander -> Selector)
- `workflow_manager.py`: Orchestrates Agent + Patch Generation
- `llm_service.py`: LLM interface (GPT-4o/Gemini) with CoT Patching
- `embedder.py`: Jina Embeddings v2
- `graph_store.py`: Knowledge graph (Neo4j)
- `indexer.py`: Repository indexing (AST + Vectors + Relations)

## License

[MIT License](LICENSE)

## Citation

If you use INSIGHT in your research, please cite:

```bibtex
@software{insight2024,
  title={INSIGHT: Automated Bug Localization with RAG},
  year={2024},
  url={https://github.com/yourusername/issue_analyzing_tool}
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open a GitHub issue.
