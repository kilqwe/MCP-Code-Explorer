import sys
import time
import subprocess
import re
from pathlib import Path
from utils import resolve_safe_path, PROJECT_ROOT
from parsers import python_parser
from tree_sitter import QueryCursor

def find_dead_code(relative_dir: str = ".") -> dict:
    """Finds Python functions that are defined but never called elsewhere in the workspace."""
    start_time = time.perf_counter()
    target_dir = resolve_safe_path(relative_dir)
    
    defined_functions = {}  
    all_text = ""          
    

    for p in target_dir.rglob("*.py"):
        if any(ignored in p.parts for ignored in ["node_modules", "venv", ".venv", ".git"]):
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            all_text += content + "\n"

            tree = python_parser.parser.parse(content.encode("utf-8"))
            cursor = QueryCursor(python_parser.OUTLINE_QUERY)
            
            for _, captures in cursor.matches(tree.root_node):
                if "func.def" in captures:
                    name_node = captures["func.name"][0] if isinstance(captures["func.name"], list) else captures["func.name"]
                    func_name = content.encode("utf-8")[name_node.start_byte:name_node.end_byte].decode("utf-8")
                    
                    # Ignore Python magic methods (e.g., __init__)
                    if not (func_name.startswith("__") and func_name.endswith("__")):
                        defined_functions[func_name] = p.relative_to(PROJECT_ROOT).as_posix()
        except Exception:
            continue
            
    dead_functions = []
    for func_name, filepath in defined_functions.items():
        # Count exact word boundaries. If it only appears once (its own definition), it's dead.
        occurrences = len(re.findall(rf"\b{re.escape(func_name)}\b", all_text))
        if occurrences == 1:
            dead_functions.append({"function": func_name, "file": filepath})
            
    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Dead code analysis completed in {elapsed:.4f} seconds.", file=sys.stderr)
    
    return {
        "functions_scanned": len(defined_functions),
        "dead_code_candidates": dead_functions
    }

def generate_churn_heatmap(relative_dir: str = ".") -> dict:
    """Finds 'Code Hotspots' by cross-referencing Git commit churn with file line counts."""
    start_time = time.perf_counter()
    target_dir = resolve_safe_path(relative_dir)
    
    try:
        # Get raw list of every file touched in git history.
        result = subprocess.run(
            ["git", "log", "--format=format:", "--name-only"],
            cwd=target_dir, capture_output=True, text=True, check=True
        )
    except Exception as e:
        return {"error": f"Requires a local git repository. {e}"}
        
    commit_counts = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and line.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
            commit_counts[line] = commit_counts.get(line, 0) + 1
            
    heatmap = []
    for rel_path, commits in commit_counts.items():
        file_path = target_dir / rel_path
        if file_path.exists():
            try:
                # Calculate LOC
                loc = sum(1 for _ in file_path.open(encoding="utf-8", errors="ignore"))
                
                heatmap.append({
                    "file": rel_path,
                    "commits": commits,
                    "loc": loc,
                    "hotspot_score": commits * loc  # High churn + High LOC = Bottleneck
                })
            except Exception:
                continue
                
    # Sort to float the biggest bottlenecks to the top
    heatmap = sorted(heatmap, key=lambda x: x["hotspot_score"], reverse=True)[:15]
    
    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Git churn heatmap generated in {elapsed:.4f} seconds.", file=sys.stderr)
    
    return {"top_hotspots": heatmap}