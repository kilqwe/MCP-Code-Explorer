import sys  
from pathlib import Path
import time
from tree_sitter import QueryCursor
from utils import resolve_safe_path
from parsers import python_parser, javascript_parser

PARSERS = {
    ".py": python_parser,
    ".js": javascript_parser,
    ".jsx": javascript_parser
}

def get_outline(relative_path: str) -> str:
    start_time = time.perf_counter()

    try:
        target = resolve_safe_path(relative_path)
    except ValueError:
        return "Error: path is outside the allowed project root."
    except FileNotFoundError:
        return f"Error: file not found at '{relative_path}'."

    ext = target.suffix
    if ext not in PARSERS:
        return f"Error: Unsupported file type '{ext}'."

    active_parser = PARSERS[ext]
    source_bytes = target.read_bytes()
    tree = active_parser.parser.parse(source_bytes)
    cursor = QueryCursor(active_parser.OUTLINE_QUERY)
    matches = cursor.matches(tree.root_node)

    def text(node):
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8")

    lines = []
    for pattern_index, captures in matches:
        if "func.def" in captures:
            def_node = captures["func.def"][0] if isinstance(captures["func.def"], list) else captures["func.def"]
            name = text(captures["func.name"][0] if isinstance(captures["func.name"], list) else captures["func.name"])
            params_node = captures.get("func.params")
            params = text(params_node[0] if isinstance(params_node, list) else params_node) if params_node else "()"
            
            start_line = def_node.start_point[0] + 1
            end_line = def_node.end_point[0] + 1
            class_name = active_parser.enclosing_class_name(def_node, source_bytes)
            prefix = f"{class_name}." if class_name else ""
            lines.append(f"def {prefix}{name}{params}  — lines {start_line}-{end_line}")

        elif "class.def" in captures:
            def_node = captures["class.def"][0] if isinstance(captures["class.def"], list) else captures["class.def"]
            name = text(captures["class.name"][0] if isinstance(captures["class.name"], list) else captures["class.name"])
            start_line = def_node.start_point[0] + 1
            end_line = def_node.end_point[0] + 1
            lines.append(f"class {name}  — lines {start_line}-{end_line}")

    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Structural outline for '{relative_path}' generated in {elapsed:.4f} seconds.", file=sys.stderr)
    
    return "\n".join(lines) if lines else "No functions or classes found."

def get_function_source(relative_path: str, function_name: str) -> str:
    start_time = time.perf_counter()

    try:
        target = resolve_safe_path(relative_path)
    except ValueError:
        return "Error: path is outside the allowed project root."
    except FileNotFoundError:
        return f"Error: file not found at '{relative_path}'."

    ext = target.suffix
    if ext not in PARSERS:
        return f"Error: Unsupported file type '{ext}'."

    active_parser = PARSERS[ext]
    source_bytes = target.read_bytes()
    tree = active_parser.parser.parse(source_bytes)
    cursor = QueryCursor(active_parser.OUTLINE_QUERY)
    matches = cursor.matches(tree.root_node)

    def text(node):
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8")

    for pattern_index, captures in matches:
        if "func.def" not in captures:
            continue

        def_node = captures["func.def"][0] if isinstance(captures["func.def"], list) else captures["func.def"]
        name = text(captures["func.name"][0] if isinstance(captures["func.name"], list) else captures["func.name"])

        class_name = active_parser.enclosing_class_name(def_node, source_bytes)
        qualified_name = f"{class_name}.{name}" if class_name else name

        if qualified_name == function_name:
            elapsed = time.perf_counter() - start_time
            # Notice file=sys.stderr added here:
            print(f"[METRIC] Source extraction for '{function_name}' completed in {elapsed:.4f} seconds.", file=sys.stderr)
            return text(def_node)

    return f"Error: no function named '{function_name}' found in '{relative_path}'."