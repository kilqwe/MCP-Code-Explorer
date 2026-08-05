import sys
import time
from tree_sitter import QueryCursor
from utils import resolve_safe_path
from parsers import python_parser

def score_complexity(relative_path: str) -> dict:
    """Scores cyclomatic complexity for all functions in a Python file to identify refactor targets."""
    start_time = time.perf_counter()
    safe_path = resolve_safe_path(relative_path)
    
    if safe_path.suffix != ".py":
        return {"error": "Complexity scoring currently only supports Python files."}
        
    source_bytes = safe_path.read_bytes()
    tree = python_parser.parser.parse(source_bytes)
    outline_cursor = QueryCursor(python_parser.OUTLINE_QUERY)
    func_matches = outline_cursor.matches(tree.root_node)
    
    results = []
    
    for pattern_idx, captures in func_matches:
        if "func.def" not in captures:
            continue
            
        def_node = captures["func.def"][0] if isinstance(captures["func.def"], list) else captures["func.def"]
        name_node = captures["func.name"][0] if isinstance(captures["func.name"], list) else captures["func.name"]
        
        name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
        class_name = python_parser.enclosing_class_name(def_node, source_bytes)
        full_name = f"{class_name}.{name}" if class_name else name

        comp_cursor = QueryCursor(python_parser.COMPLEXITY_QUERY)
        comp_matches = comp_cursor.matches(def_node)
        

        score = 1 + len(comp_matches)
        
        risk = "Low"
        if score > 5: risk = "Moderate"
        if score > 10: risk = "High"
        if score > 20: risk = "Extreme"
        
        results.append({
            "function": full_name,
            "line": def_node.start_point[0] + 1,
            "complexity_score": score,
            "risk_level": risk
        })
        

    results = sorted(results, key=lambda x: x["complexity_score"], reverse=True)
    
    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Complexity analysis for '{relative_path}' completed in {elapsed:.4f} seconds.", file=sys.stderr)
    
    return {
        "file": relative_path,
        "functions_scored": len(results),
        "scores": results
    }