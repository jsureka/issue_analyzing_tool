<p align="center">
  <img src="assets/logo.PNG" alt="INSIGHT Logo" />
</p>

<h1 align="center">INSIGHT (Issue Analyzing Tool)</h1>

## What is INSIGHT?

INSIGHT is an open-source GitHub application that acts as an intelligent issue management assistant. It leverages **Agentic RAG (Retrieval-Augmented Generation)** and **Large Language Models (LLMs)** to provide deep technical analysis and automated bug localization.

**Key Features:**

1.  **Agentic Bug Localization**: Uses a multi-step reasoning workflow (LangGraph) to identify buggy files with high precision.
2.  **Technical Analysis & Patching**: Generates detailed explanations of *why* a bug is occurring and suggests concrete code fixes (patches) using Google Gemini 2.0.
3.  **Graph-Based Context**: Utilizes **GraphRAG** (Knowledge Graph + Vector Search) to understand the structural relationships and directory context of your codebase.
4.  **Duplicate Detection**: Identifies similar existing issues to prevent redundancy.
5.  **Severity Prediction**: Automatically classifies issue severity (Blocker, Critical, Major, Minor, Trivial).

---

## Documentation

- **[Architecture Guide](ARCHITECTURE.md)**: Detailed overview of the Agentic RAG system, LangGraph workflow, and component design.
- **[Usage Manual](USAGE_MANUAL.md)**: Comprehensive guide on installation, configuration, and testing.

---

## Install INSIGHT

INSIGHT can be installed as a GitHub app on any GitHub repository.

:link: [Install INSIGHT](https://github.com/apps/insight-issue-analyzing-tool)

---

## System Architecture

INSIGHT is built on a modern **Agentic RAG** architecture:

<p align="center">
  <img src="assets/architecture.png" alt="INSIGHT Architecture" />
</p>

1.  **Knowledge Base Layer**:
    *   **Vector Store (FAISS)**: For semantic code search.
    *   **Graph Store (Neo4j)**: For structural code relationships and directory summaries.
2.  **Agentic Workflow (LangGraph)**:
    *   Orchestrates a reasoning loop: **Retrieve Context** -> **Analyze Bug** -> **Generate Hypothesis** -> **Suggest Patch**.
3.  **LLM Service**:
    *   Powered by **Google Gemini 2.0 Flash** for fast, accurate code reasoning.
4.  **Event Handler**:
    *   Processes GitHub Webhooks (Issues, Installations) in real-time.

---

## Quick Start

### Prerequisites

*   Python 3.11+
*   Neo4j Database (for GraphRAG features)
*   Google Gemini API Key

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/sea-lab-wm/sprint_issue_report_assistant_tool.git
    cd issue_analyzing_tool/INSIGHT\ Tool
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file with your credentials (see [Usage Manual](USAGE_MANUAL.md#step-2-configure-environment)).

4.  **Run the Application**:
    ```bash
    python main.py
    ```

---

## Contributing

We welcome contributions! Please see our [Contribution Guidelines](CONTRIBUTING.md) for more details.

**Maintainers**:
*   [Jitesh Sureka](https://github.com/jsureka)
*   [Ahmed Adnan](https://github.com/adnan23062000)
*   [Antu Saha](https://github.com/antu-saha)
*   [Oscar Chaparro](https://github.com/oscarchaparro)

---

## License

This project is licensed under the MIT License.
