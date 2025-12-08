# INSIGHT - Automated Bug Localization Tool

[![GitHub](https://img.shields.io/badge/GitHub-App-blue)](https://github.com/apps/insight-issues)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

INSIGHT is a GitHub application that automatically localizes bugs in software repositories using a RAG (Retrieval-Augmented Generation) pipeline. It analyzes GitHub issues and identifies the specific files and functions that need to be modified to fix the bug.

## Features

✨ **RAG-Based Localization**: Combines dense vector retrieval with LLM-powered analysis  
🎯 **Smart Query Generation**: LLM generates optimized search queries from issue descriptions  
📊 **Knowledge Graph**: Enriches candidates with caller/callee relationships  
🌍 **Multi-Language**: Supports Python, Java, and Kotlin  
⚡ **Auto-Updates**: Automatically updates knowledge base when code changes  
📈 **High Accuracy**: 76.67% Hit@3 on LCA benchmark

## How It Works

1. **Issue Received**: GitHub webhook triggers when an issue is opened
2. **Query Generation**: LLM creates an optimized search query
3. **Dense Retrieval**: Retrieves top-20 candidate entities (Files, Classes, Functions) using semantic search
4. **Graph Enrichment**: Adds caller/callee context from code knowledge graph
5. **LLM Selection**: Selects top-5 most likely buggy entities
6. **Analysis & Patch**: LLM explains the bug and suggests a fix
7. **Comment Posted**: Analysis posted as a GitHub comment

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

**File-Level (k=3)**:
- **Hit@3**: 76.67% (found buggy file in top 3 in 76.67% of cases)
- **Precision@3**: 35.56%
- **Recall@3**: 50.06%
- **F1@3**: 38.47%
- **MAP**: 0.4377

**Function-Level (k=3)**:
- **Hit@3**: 13.33%
- **F1@3**: 5.24%

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture.

**Key Components**:
- `bug_localization.py`: Main RAG pipeline
- `llm_service.py`: LLM interface (GPT-4o/Gemini)
- `retriever.py`: Dense retrieval (FAISS + UnixCoder)
- `graph_store.py`: Knowledge graph (Neo4j)
- `indexer.py`: Repository indexing
- `workflow_manager.py`: LangGraph orchestration (optional)

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
