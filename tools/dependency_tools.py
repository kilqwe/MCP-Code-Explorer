import sys
import time
from utils import resolve_safe_path
from parsers import python_parser

def get_imports(relative_path: str) -> dict:
    """
    Extracts all module dependencies and import statements from a Python file.
    """
    start_time = time.perf_counter()
    safe_path = resolve_safe_path(relative_path)
    
    if safe_path.suffix != ".py":
        return {"error": f"Import extraction currently only supports Python files."}
        
    source_bytes = safe_path.read_bytes()
    imports = python_parser.extract_imports(source_bytes)
    
    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Dependency extraction for '{relative_path}' completed in {elapsed:.4f} seconds.", file=sys.stderr)
    
    return {
        "file": relative_path,
        "import_count": len(imports),
        "imports": sorted(imports)
    }