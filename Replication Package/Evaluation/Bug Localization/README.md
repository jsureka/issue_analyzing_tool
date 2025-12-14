
# Bug Localization Evaluation

This directory contains the scripts and data required to reproduce the bug localization evaluation of the INSIGHT tool.

## Overview

The evaluation assesses the tool's ability to identify relevant files, classes, and functions for a given issue. It uses a test dataset of real-world issues from various repositories.

## Prerequisites

- Python 3.8+
- The INSIGHT tool environment (dependencies installed)
- `test_dataset.xlsx` (located in the parent `Evaluation` directory)

## How to Run

1. Navigate to this directory:
   ```bash
   cd "Replication Package/Evaluation/Bug Localization"
   ```

2. Run the evaluation script:
   ```bash
   python evaluate_bug_localization.py
   ```

   **Note:** This process involves:
   - Reading the `test_dataset.xlsx`.
   - Cloning the repositories specified in the dataset to a `temp_repos` directory given in the root folder.
   - Indexing the repositories using the INSIGHT tool's indexing engine (if not already indexed).
   - Running the bug localization pipeline for each issue.
   - Calculating metrics (Hit@k, Precision, Recall, etc.).

3. **Output**:
   - `evaluation_results_bug_localization.xlsx`: Contains three sheets:
     - `File Level Metrics`: Summary metrics for file-level localization.
     - `Func_Class Level Metrics`: Summary metrics for function and class-level localization.
     - `Detailed Results`: Per-issue detailed metrics and debug info.
   - `evaluation_log.txt`: Detailed logs of the execution.

## Evaluation Results

The following tables summarize the results of the bug localization evaluation on the test dataset.

### File Level Metrics

|                               |   Hit@1 |   Hit@3 |   Hit@5 |   Precision@5 |   Recall@5 |   All Correct@5 |   All Incorrect@5 |
|:------------------------------|--------:|--------:|--------:|--------------:|-----------:|----------------:|------------------:|
| amwa-tv/nmos-testing          |    0.4  |    0.4  |    0.5  |         0.5   |   0.5      |            0.5  |              0.5  |
| aws/chalice                   |    0.5  |    0.5  |    0.6  |         0.46  |   0.315    |            0.1  |              0.4  |
| hazelcast/hazelcast-simulator |    0.2  |    0.3  |    0.5  |         0.26  |   0.141111 |            0    |              0.5  |
| ioos/compliance-checker       |    0.2  |    0.3  |    0.3  |         0.3   |   0.2      |            0.1  |              0.7  |
| tootallnate/java-websocket    |    0.8  |    0.8  |    0.8  |         0.75  |   0.64     |            0.5  |              0.2  |
| **Total**                     |  **0.42** |  **0.46** |  **0.54** |       **0.454** | **0.359222** |          **0.24** |            **0.46** |

### Function/Class Level Metrics

|                               |   Hit@1 |   Hit@3 |   Hit@5 |   Precision@5 |   Recall@5 |   All Correct@5 |   All Incorrect@5 |
|:------------------------------|--------:|--------:|--------:|--------------:|-----------:|----------------:|------------------:|
| amwa-tv/nmos-testing          |    0.1  |    0.4  |    0.4  |         0.4   |   0.4      |            0.4  |              0.6  |
| aws/chalice                   |    0    |    0.2  |    0.2  |         0.2   |   0.15     |            0.1  |              0.8  |
| hazelcast/hazelcast-simulator |    0    |    0.4  |    0.4  |         0.24  |   0.138889 |            0    |              0.6  |
| ioos/compliance-checker       |    0    |    0.1  |    0.1  |         0.1   |   0.05     |            0    |              0.9  |
| tootallnate/java-websocket    |    0.1  |    0.3  |    0.3  |         0.3   |   0.3      |            0.3  |              0.7  |
| **Total**                     |  **0.04** |  **0.28** |  **0.28** |       **0.248** | **0.207778** |          **0.16** |            **0.72** |
