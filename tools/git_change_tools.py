import subprocess
import sys
import time
from pathlib import Path
from utils import PROJECT_ROOT, resolve_safe_path
from parsers import python_parser
from tree_sitter import QueryCursor

def analyze_git_changes(relative_dir: str = ".") -> dict:
    """
    Runs git diff to identify uncommitted line changes and maps them 
    directly to affected AST functions and classes.
    """
    start_time = time.perf_counter()
    target_dir = resolve_safe_path(relative_dir)

    try:
        # Run git diff to get unified diff output.
        result = subprocess.run(
            ["git", "diff", "-U0"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=True
        )
        diff_output = result.stdout
    except Exception as e:
        return {"error": f"Failed to run git diff: {e}. Ensure git is installed and directory is a git repository."}

    if not diff_output.strip():
        return {"message": "No uncommitted changes detected in the git repository."}

    # Parse diff output to collect modified line numbers per file.
    modified_files = {}
    current_file = None

    for line in diff_output.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            if current_file.endswith(".py"):
                modified_files[current_file] = set()
            else:
                current_file = None
        elif line.startswith("@@") and current_file:

            try:
                parts = line.split(" ")
                added_part = parts[2]
                if "," in added_part:
                    start_line, count = map(int, added_part[1:].split(","))
                else:
                    start_line = int(added_part[1:])
                    count = 1
                for l in range(start_line, start_line + max(1, count)):
                    modified_files[current_file].add(l)
            except Exception:
                continue

    impacted_components = {}

    for rel_file, lines in modified_files.items():
        file_path = target_dir / rel_file
        if not file_path.exists() or not lines:
            continue

        try:
            source_bytes = file_path.read_bytes()
            tree = python_parser.parser.parse(source_bytes)
            cursor = QueryCursor(python_parser.OUTLINE_QUERY)
            matches = cursor.matches(tree.root_node)

            affected_funcs = []
            for pattern_idx, captures in matches:
                if "func.def" not in captures:
                    continue

                def_node = captures["func.def"][0] if isinstance(captures["func.def"], list) else captures["func.def"]
                name_node = captures["func.name"][0] if isinstance(captures["func.name"], list) else captures["func.name"]

                func_start = def_node.start_point[0] + 1
                func_end = def_node.end_point[0] + 1

                # Check if any modified line falls inside this function
                if any(func_start <= l <= func_end for l in lines):
                    func_name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                    class_name = python_parser.enclosing_class_name(def_node, source_bytes)
                    full_name = f"{class_name}.{func_name}" if class_name else func_name
                    affected_funcs.append({
                        "function": full_name,
                        "span": f"lines {func_start}-{func_end}"
                    })

            impacted_components[rel_file] = {
                "modified_line_count": len(lines),
                "affected_functions": affected_funcs
            }
        except Exception as e:
            impacted_components[rel_file] = {"error": str(e)}

    elapsed = time.perf_counter() - start_time
    print(f"[METRIC] Git change impact analysis completed in {elapsed:.4f} seconds.", file=sys.stderr)

    return {
        "status": "success",
        "impacted_files": impacted_components
    }