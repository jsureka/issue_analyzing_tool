# SPRINT Product Overview

SPRINT (iSsue rePoRt assIstaNT) is an open-source GitHub application that provides automated bug localization assistance for software development teams.

## Core Feature

**Knowledge Base Bug Localization** - Uses vector similarity search and code analysis to predict which code files likely need modification to resolve reported issues. The system builds a knowledge base of the repository's code structure and uses semantic search to find relevant files and functions.

## Target Users

- Developers and project managers
- Computer science students and educators
- Open source maintainers managing GitHub repositories

## Integration

SPRINT operates as a GitHub App that monitors repository webhooks and automatically processes new issues, providing bug localization predictions through issue comments.
