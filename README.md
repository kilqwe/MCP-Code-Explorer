# MCP Codebase Analyzer

A Model Context Protocol (MCP) server that lets an LLM explore a codebase structurally — outlines, signatures, dependencies, complexity, and change impact — instead of ingesting raw files into context.

**Status: complete, archived as a learning project.** See [Status](#status) for what held up and what didn't.

## The Premise

Feeding entire files or repositories into an LLM's context window wastes tokens and increases hallucination risk. If someone asks "what does `read_file` do," the model doesn't need the whole file — it needs the function's signature and maybe its body, nothing else.

This server parses code into an Abstract Syntax Tree using **Tree-sitter** and exposes that structure through MCP tools, so a client can query exactly what it needs and drill deeper only when the task requires it.

That premise was sound when this was started. It is largely no longer true — see [Status](#status).

## Tech Stack

- **Python 3.13**
- **FastMCP** — MCP server framework (stdio transport)
- **Tree-sitter** (+ grammars for Python and JavaScript) — structural parsing
- **Git** (via subprocess) — diff and change-impact analysis
- **MCP Inspector** — protocol-level testing and debugging

## Tools

Thirteen tools, as registered in `server.py`:

| Tool | Description |
|---|---|
| `ping` | Connection smoke test. |
| `read_file` | Raw file text, path-bounded to the project root. |
| `scan_directory` | Recursive walk with noise pruning (`.venv`, `node_modules`, `.git`, caches). Returns an outline per Python/JS file plus a flat list of other files. Unpaginated. |
| `get_outline` | Function and class signatures with line ranges for one file. Names and parameters only — no return types or docstrings. |
| `get_function_source` | Exact source of one named function or method (`Class.method`). |
| `search_symbols` | Substring match on function and class names, by parsing the tree via `scan_directory`. |
| `search_code` | Regex search across code files. Always case-insensitive; capped at 20 matches per file. |
| `get_imports` | Import statements from a Python file, deduplicated. Python only. |
| `score_complexity` | Cyclomatic complexity per function, by counting decision nodes. Python only. |
| `analyze_git_changes` | Maps `git diff` hunks to the functions and methods containing them. |
| `find_dead_code` | Flags functions whose name appears only once across the workspace. **Unreliable — see Known Limitations.** |
| `generate_churn_heatmap` | Commit frequency × file size (LOC). Must be run from the repository root. |
| `get_project_config` | Detects framework, dependencies, config files, and build/CI setup deterministically. |
| `analyze_github_repo` | Downloads a public GitHub repository zip into `repos/` so the other tools can analyze it. |

## Design Principles

- **On-demand over front-loaded.** Every tool returns the minimum structure needed to answer the next question, not the whole file.
- **Sandboxed.** All file access resolves against a configured project root and is rejected if it lands outside it.
- **Deterministic.** No LLM calls inside the analysis — every tool is a pure function of the repository state.
- **Composable.** Higher-level tools are built by combining lower-level ones rather than duplicating parsing logic.

## Security

Both issues below were found in an audit of this repository and are fixed:

- **Path containment.** Four tools (`read_file`, `scan_directory`, `get_outline`, `get_function_source`) guarded the sandbox with `str.startswith(str(PROJECT_ROOT))`. That admits any sibling directory whose name extends the root — `MCPCodeExplorer2`, `MCPCodeExplorer-backup` — which, combined with `read_file`, is arbitrary file read. All four now route through `resolve_safe_path`, which uses `Path.is_relative_to`. The containment check runs before the existence check, so out-of-root paths do not leak whether a file exists.
- **Untrusted archives.** `analyze_github_repo` fetches arbitrary third-party zips. It now validates `owner`/`repo`/`branch` before interpolating them into the URL, caps download size (100 MB), declared expanded size (500 MB) and entry count (20,000), sets a request timeout, and refuses any archive containing an entry that resolves outside `repos/`.

One clarification, since it is a common assumption: CPython's `zipfile.extractall` already strips `..` components, leading separators and drive letters from member names, so this code was **not** vulnerable to classic zip-slip. Verified against Python 3.13 — every hostile entry landed inside the destination. The containment check is defense in depth and makes the guarantee explicit rather than an inherited implementation detail; the size caps address the real gap, which was unbounded resource use.

## Known Limitations

Documented rather than hidden. Several of these are why the project stops here.

- **`PROJECT_ROOT` is a hardcoded absolute path** (`utils.py:5`). It must be edited before the server runs anywhere else. Because `analyze_github_repo` extracts into it, downloaded repositories land inside this source tree, and `SKIP_DIRS` does not exclude `repos/` — so a workspace-wide scan mixes this project's files with its analysis targets.
- **`find_dead_code` should not be acted on.** It concatenates the workspace and counts `\bname\b` occurrences; exactly one means "dead." Measured against ground truth on this workspace plus Flask: 966 functions scanned, ~450 flagged, **2** true positives. Everything framework-invoked — pytest tests, route handlers, callbacks — is reported as dead. It also keys functions by bare name, so same-named functions in different files overwrite each other, and it counts matches inside comments and strings.
- **`generate_churn_heatmap` fails silently outside the repository root.** `git` returns paths relative to the repo root, but they are joined against the target directory. Root returns 15 hotspots; `tools/` returns 0 with no error.
- **JavaScript support is outline-only.** No complexity or import queries, no docstring capture, and the outline query matches only `function_declaration`, `method_definition` and `class_declaration` — so `const f = () => {}` is invisible. `.jsx` maps to the JS parser; there is no TypeScript grammar.
- **`scan_directory` is unpaginated** and re-parses every file on every call. Flask produces roughly 114,000 characters in a single response. `search_symbols` triggers that full parse just to substring-match names.
- **Error conventions are inconsistent.** Most tools return error strings or dicts (which a model reads as data), while `resolve_safe_path` raises (which a model reads as a tool failure).
- **Dead code in the parser layer.** `parse_outline_data` and `extract_function_source` in `python_parser.py` are never called and would raise if they were — they look up `function.name` captures where the query defines `@func.name`. `first_doc_line` is only reachable from them, which is why outlines carry no docstrings.
- **No tests, and no packaging.** `requirements.txt` is a UTF-16 `pip freeze` artifact with 72 flat transitive pins. `tree-sitter==0.26.0`'s `QueryCursor` API is recent; an unpinned bump breaks every parser.

## Running Locally

```bash
git clone <this-repo>
cd MCPCodeExplorer
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

**Before running, edit `PROJECT_ROOT` in `utils.py` to the absolute path you want to analyze.** It is not configurable at runtime, and every tool is bounded by it.

```bash
fastmcp run server.py
```

Test with [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector fastmcp run server.py
```

Or connect it to Claude Desktop as an MCP server for real LLM tool-use testing.

## Status

Phase 1 of a planned three-phase project — and the end of it. An audit against ground truth (every tool run and its output checked, not just read) reached a clear conclusion:

**Ten of the thirteen tools duplicate what an agentic client already does natively**, and mostly do it worse. Claude Code, Cursor and similar clients don't dump repositories into context — they glob, grep, read targeted ranges, and delegate to subagents whose intermediate reads never reach the main context. An unpaginated `scan_directory` response is *less* context-efficient than what those clients do without any server at all. The premise was correct in 2023; it was solved at the client layer, not the server layer.

Two tools justified their existence: **`analyze_git_changes`** (diff hunks → affected functions) and **`get_project_config`** (deterministic project detection).

Kept public as a learning project and a reference implementation of a small, cleanly layered FastMCP server — `server.py` is a pure facade, and adding a tool is one module plus one decorator. That structure is the part worth reusing.

Work continues in a separate project on **test impact selection for pytest**: from a diff, determine which tests can possibly be affected and run only those. It reuses the diff-to-symbol mapping from `analyze_git_changes`, has a measurable correctness criterion (run the full suite and check whether anything skipped would have failed), and ships as a `pytest` plugin rather than an MCP server — installable and evaluable without an MCP client.

The originally planned Phases 2–3 (a self-hosted home server, then merging infrastructure management into this server) are deliberately **not** happening in this repo. "Structured query over raw dump" is a description of good API design, not a shared architecture: it buys no common code between a Tree-sitter parser and a systemd controller. Code analysis is read-only and safe to run speculatively; infrastructure control is stateful, destructive, and needs authorization and audit. They should not share a process, a sandbox model, or a permission surface. MCP already lets a client connect to several servers at once, which is the right seam.
