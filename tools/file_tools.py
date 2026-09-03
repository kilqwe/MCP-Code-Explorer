import sys  # Test comment
from pathlib import Path
import os
import time
from utils import PROJECT_ROOT, SKIP_DIRS, resolve_safe_path
from tools.outline_tools import get_outline

def read_file(relative_path: str) -> str:
    """Reads and returns the raw text content of a file within the project root."""
    try:
        target = resolve_safe_path(relative_path)
    except ValueError:
        return "Error: path is outside the allowed project root."
    except FileNotFoundError:
        return f"Error: file not found at '{relative_path}'."
    if not target.is_file():
        return f"Error: '{relative_path}' is not a file."
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"

def scan_directory(relative_dir: str = ".") -> dict:
    """Recursively scans a directory with metrics."""
    start_time = time.perf_counter()
    
    try:
        start_dir = resolve_safe_path(relative_dir)
    except ValueError:
        return {"error": "path is outside the allowed project root."}
    except FileNotFoundError:
        return {"error": f"'{relative_dir}' is not a valid directory."}
    if not start_dir.is_dir():
        return {"error": f"'{relative_dir}' is not a valid directory."}

    python_files = {}
    other_files = []

    for root, dirs, files in os.walk(start_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(PROJECT_ROOT).as_posix()

            if filename.endswith((".py", ".js", ".jsx")):
                outline = get_outline(rel_path)
                python_files[rel_path] = outline
            else:
                other_files.append(rel_path)

    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Directory scan for '{relative_dir}' completed in {elapsed:.4f} seconds.", file=sys.stderr)

    return {
        "python_files": python_files,
        "other_files": other_files,
    }