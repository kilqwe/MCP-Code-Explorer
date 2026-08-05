import os
import re
from pathlib import Path
from utils import PROJECT_ROOT, SKIP_DIRS, resolve_safe_path
from tools import file_tools

def search_symbols(query: str, relative_dir: str = ".") -> dict:
    """
    Searches parsed structural outlines across the workspace for function 
    or class names matching the query string.
    """
    scan_results = file_tools.scan_directory(relative_dir)
    
    if "error" in scan_results:
        return scan_results

    source_files = scan_results.get("python_files", {})
    
    query_lower = query.lower()
    matches = {}
    
    for file_path, outline in source_files.items():
        if isinstance(outline, str):
            matched_lines = [
                line for line in outline.splitlines() 
                if query_lower in line.lower()
            ]
            if matched_lines:
                matches[file_path] = matched_lines
                
    return matches


def search_code(pattern: str, relative_dir: str = ".") -> dict:
    """
    Performs a regex search across all non-ignored project files to locate 
    code snippets, variable usages, or exact text strings.
    """
    base_path = resolve_safe_path(relative_dir)
    
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"error": f"Invalid regex pattern: {e}"}
        
    results = {}

    allowed_extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".txt", ".json"}

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for filename in files:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(PROJECT_ROOT).as_posix()
            
            # THE FIX: Skip files that aren't in our allowed text list
            if full_path.suffix.lower() not in allowed_extensions:
                continue
            
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                matching_lines = []
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        matching_lines.append(f"Line {line_num}: {line.strip()}")
                        
                if matching_lines:
                    results[rel_path] = matching_lines[:20]  
            except Exception:
                continue

    return results