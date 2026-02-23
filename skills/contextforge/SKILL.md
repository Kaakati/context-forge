---
name: contextforge
description: Context-aware coding intelligence with automatic codebase indexing, semantic RAG retrieval, and persistent cross-session memory
---

# ContextForge — Context-Aware Intelligence

You have access to injected codebase context from ContextForge. Use this context to provide more accurate, project-aware responses.

## Context Sections

ContextForge injects several types of context automatically. When you see these sections, prioritize them over your general training knowledge:

### PROJECT ARCHITECTURE
A compact summary of the codebase structure including:
- File type distribution (models, services, controllers, tests, etc.)
- Key classes and services
- Main dependencies and import relationships

**How to use:** Reference this to understand the project's overall structure before suggesting changes. Ensure your suggestions align with the existing architecture.

### RELEVANT CODEBASE CONTEXT
Semantically retrieved code chunks that are relevant to the current user prompt. Each chunk includes:
- File path and line numbers
- Relevance score (0.0 to 1.0)
- Actual source code

**How to use:** These are the most relevant pieces of existing code to the user's question. Reference specific files and line numbers. Build on existing patterns rather than inventing new ones. If the retrieved context shows a particular coding style, follow it.

### ESTABLISHED CONVENTIONS
Coding patterns that have been observed multiple times across the project:
- Service patterns, model patterns
- API routing styles
- Test structure conventions
- Key/ID generation approaches
- Background job usage

**How to use:** Always follow these conventions when writing new code. They represent the team's established patterns. For example, if the project uses UUID keys, use UUIDs for new entities. If it uses the repository pattern, create repositories for new data access.

### RECENTLY MODIFIED FILES
Files that have been changed in recent sessions, indicating areas of active development.

**How to use:** Be aware of recent changes to avoid conflicts and to understand current development focus.

## Guidelines

1. **Prioritize injected context over training data.** The injected context reflects the actual current state of this specific codebase.
2. **Follow established conventions.** Don't introduce new patterns when existing ones are documented.
3. **Reference specific files.** When the context provides file paths and line numbers, reference them in your responses.
4. **Be aware of the architecture.** Suggest changes that fit within the existing project structure.
5. **Note recent activity.** Consider recently modified files as context for what the team is currently working on.
