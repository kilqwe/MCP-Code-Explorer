from fastmcp import FastMCP
from tools import audit_tools, complexity_tools, file_tools, git_change_tools, outline_tools, github_tools, search_tools, dependency_tools, config_tools

mcp = FastMCP("CodeAnalyzer")

@mcp.tool()
def ping(message: str) -> str:
    """Dummy tool to verify connection."""
    return f"Pong: {message}"

@mcp.tool()
def read_file(relative_path: str) -> str:
    """Reads raw file contents safely from the project root."""
    return file_tools.read_file(relative_path)

@mcp.tool()
def scan_directory(relative_dir: str = ".") -> dict:
    """
    Scans directory recursively, skipping virtual environments and caches.
    Returns structural outlines for Python files and lists other files.
    """
    return file_tools.scan_directory(relative_dir)

@mcp.tool()
def get_outline(relative_path: str) -> str:
    """Returns the structural outline (classes, functions, docs) of a Python file."""
    return outline_tools.get_outline(relative_path)

@mcp.tool()
def get_function_source(relative_path: str, function_name: str) -> str:
    """Extracts the exact source code of a specific function or method (e.g. 'Class.method')."""
    return outline_tools.get_function_source(relative_path, function_name)

@mcp.tool()
def analyze_github_repo(owner: str, repo: str, branch: str = "main") -> dict:
    """Downloads a public GitHub repo so it can be analyzed using scan_directory and get_outline."""
    return github_tools.analyze_github_repo(owner, repo, branch)

@mcp.tool()
def search_symbols(query: str, relative_dir: str = ".") -> dict:
    """Finds classes or functions matching a name query across the workspace."""
    return search_tools.search_symbols(query, relative_dir)

@mcp.tool()
def search_code(pattern: str, relative_dir: str = ".") -> dict:
    """Performs regex search across code files in the workspace to find variable usages or text strings."""
    return search_tools.search_code(pattern, relative_dir)

@mcp.tool()
def get_imports(relative_path: str) -> dict:
    """Extracts all imported modules and statements from a Python file."""
    return dependency_tools.get_imports(relative_path)

@mcp.tool()
def score_complexity(relative_path: str) -> dict:
    """Calculates the cyclomatic complexity of functions in a Python file to identify complex code."""
    return complexity_tools.score_complexity(relative_path)

@mcp.tool()
def analyze_git_changes(relative_dir: str = ".") -> dict:
    """Analyzes uncommitted git changes and maps modified lines directly to affected Python functions."""
    return git_change_tools.analyze_git_changes(relative_dir)

@mcp.tool()
def find_dead_code(relative_dir: str = ".") -> dict:
    """Finds Python functions that are defined but never called elsewhere in the workspace."""
    return audit_tools.find_dead_code(relative_dir)

@mcp.tool()
def generate_churn_heatmap(relative_dir: str = ".") -> dict:
    """Identifies architectural bottlenecks by combining Git commit frequency with file size (LOC)."""
    return audit_tools.generate_churn_heatmap(relative_dir)

@mcp.tool()
def get_project_config(relative_dir: str = ".") -> dict:
    """Detects the project's framework, dependencies, config files, and build/CI setup deterministically."""
    return config_tools.get_project_config(relative_dir)

if __name__ == "__main__":
    mcp.run()