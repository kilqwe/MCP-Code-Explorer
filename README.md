# MCP Codebase Analyzer

A Model Context Protocol (MCP) server that lets an LLM explore a codebase structurally - outlines, signatures, dependencies, complexity, and change impact, instead of ingesting raw files into context.

## The Problem

Feeding entire files or repositories into an LLM's context window wastes tokens and increases hallucination risk. Most of that content is irrelevant to any given question. If someone asks "what does `read_file` do," the model doesn't need the whole file — it needs the function's signature, docstring, and maybe its body, nothing else.

## The Approach

Instead of dumping raw text, this server parses code into an Abstract Syntax Tree using **Tree-sitter** and exposes that structure through a set of MCP tools. An LLM client (e.g. Claude Desktop) can query exactly what it needs, a directory outline, one function's source, an import graph, a complexity score and drill deeper only when the task requires it. The result is a smaller, more precise context footprint and fewer tokens spent on irrelevant code.

## Tech Stack

- **Python 3.13**
- **FastMCP** - MCP server framework
- **Tree-sitter** (+ language grammars for Python and JavaScript) - structural parsing
- **Git** (via subprocess) - diff and change-impact analysis
- **GitHub API** - remote repository ingestion
- **MCP Inspector** - protocol-level testing and debugging

## Tools

| Tool | Description |
|---|---|
| `scan_directory` | High-speed recursive directory traversal with noise pruning (`.venv`, `node_modules`, `.git`, etc). |
| `get_outline` | Maps out function and class definitions, signatures, return types, docstrings, and line numbers for a file. |
| `get_function_source` | Extracts the exact source of a single named function or method. |
| `search_symbols` | AST-aware symbol lookup across the workspace (finds definitions, not just text matches). |
| `search_code` | Regex-based text search across allowed file types. |
| `get_imports` | Maps how internal and external modules connect to one another. |
| `score_complexity` | Calculates cyclomatic complexity per function to highlight refactor targets. |
| `analyze_git_changes` | Maps uncommitted git modifications to the specific functions they affect. |
| `analyze_dead_code` | Cross-references defined functions against usage to flag likely-unused code. |
| `analyze_churn_heatmap` | Combines file size with git commit frequency to surface large, frequently-changed files — a common code-smell signal. |
| `analyze_github_repo` | Downloads and mounts a remote GitHub repository into a local sandbox for the same structural analysis. |

## Design Principles

- **On-demand over front-loaded.** Every tool returns the minimum structure needed to answer the next question, not the whole file.
- **Sandboxed by default.** All file access is path-bounded to a configured project root, preventing traversal outside the allowed workspace.
- **Composable.** Higher-level tools (dead code detection, churn heatmaps) are built by combining outputs from lower-level tools (outline, search, git) rather than duplicating parsing logic.
- **Language-extensible.** Tree-sitter's grammar model means adding a new language is a matter of adding a grammar + query, not rewriting the architecture.

## Status

Phase 1 of a three-phase project. Phase 2 is a self-hosted home server (reverse proxy, monitoring, CI/CD). Phase 3 merges the two: applying this same "structured query over raw dump" philosophy to infrastructure — an LLM querying and managing a live server the same way it queries a codebase here.

## Running Locally

```bash
git clone <this-repo>
cd mcp-codebase-analyzer
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
fastmcp run server.py
```

Test with [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector fastmcp run server.py
```

Or connect it to Claude Desktop as an MCP server for real LLM tool-use testing.
