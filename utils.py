from pathlib import Path

SKIP_DIRS = {"venv", ".venv", "node_modules", ".git", "__pycache__", ".pytest_cache"}

PROJECT_ROOT = Path(r"C:\Users\shrey\Desktop\MCPCodeExplorer").resolve()

def first_doc_line(raw_doc_text):
    stripped = raw_doc_text.strip().strip('"""').strip("'''")
    non_blank_lines = [line.strip() for line in stripped.split("\n") if line.strip()]
    if not non_blank_lines:
        return ""
    first = non_blank_lines[0]
    if len(non_blank_lines) > 1:
        return f"{first}..."
    return first

def resolve_safe_path(relative_path: str) -> Path:
    """
    Resolves a relative path against PROJECT_ROOT and ensures it is secure.
    Prevents directory traversal attacks (e.g., passing '../' to escape the root).
    """

    target_path = (PROJECT_ROOT / relative_path).resolve()

    if not target_path.is_relative_to(PROJECT_ROOT):
        raise ValueError(
            f"Security Error: The path '{relative_path}' attempts to access files"
            f"outside the allowed project root ({PROJECT_ROOT})."
        )
    
    if not target_path.exists():
        raise FileNotFoundError(f"The path '{target_path}' does not exist.")
        
    return target_path