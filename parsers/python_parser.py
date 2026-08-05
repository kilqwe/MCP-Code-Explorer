from pathlib import Path
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython
from utils import first_doc_line


PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

OUTLINE_QUERY = Query(PY_LANGUAGE, """
(function_definition
  name: (identifier) @func.name
  parameters: (parameters) @func.params
  return_type: (type)? @func.return_type
  body: (block . (expression_statement (string) @func.docstring)?)
) @func.def

(class_definition
  name: (identifier) @class.name
  body: (block . (expression_statement (string) @class.docstring)?)
) @class.def
""")

def enclosing_class_name(func_def_node, source_bytes):
    """Walk up the tree from a function_definition node; return the
    enclosing class name if this function is a method, else None."""
    node = func_def_node.parent
    while node is not None:
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
        node = node.parent
    return None
  
def parse_outline_data(source_bytes: bytes) -> str:
    """Takes raw bytes and returns the formatted outline string."""
    tree = parser.parse(source_bytes)
    cursor = QueryCursor()
    matches = cursor.matches(OUTLINE_QUERY, tree.root_node)
    
    outline_lines = []
    
    # Iterate through matches using the cursor
    for match in matches:
        captures = match[1] if isinstance(match, tuple) else match.captures
        
        # Check if this match is a class or a function
        if "class.name" in captures:
            class_name = captures["class.name"][0].text.decode("utf-8")
            doc_node = captures.get("class.docstring")
            docstring = doc_node[0].text.decode("utf-8").strip('\'"') if doc_node else None
            
            doc_display = f" # {first_doc_line(docstring)}" if docstring else ""
            outline_lines.append(f"class {class_name}:{doc_display}")
            
        elif "function.name" in captures:
            func_name = captures["function.name"][0].text.decode("utf-8")
            func_node = captures["function.def"][0]
            
            # Prepend class name if method.
            parent_class = enclosing_class_name(func_node)
            qual_name = f"{parent_class}.{func_name}" if parent_class else func_name
            
            # Extract params and return type
            params = captures["function.params"][0].text.decode("utf-8") if "function.params" in captures else "()"
            ret_type_node = captures.get("function.return")
            ret_type = f" -> {ret_type_node[0].text.decode('utf-8')}" if ret_type_node else ""
            
            # Extract docstring
            doc_node = captures.get("function.docstring")
            docstring = doc_node[0].text.decode("utf-8").strip('\'"') if doc_node else None
            doc_display = f" # {first_doc_line(docstring)}" if docstring else ""
            
            outline_lines.append(f"def {qual_name}{params}{ret_type}:{doc_display}")

    return "\n".join(outline_lines) if outline_lines else "No classes or functions found."

def extract_function_source(source_bytes: bytes, target_func_name: str) -> str:
    """Takes raw bytes and returns the exact source string of the targeted function."""
    tree = parser.parse(source_bytes)
    cursor = QueryCursor()
    matches = cursor.matches(OUTLINE_QUERY, tree.root_node)
    
    for match in matches:
        captures = match[1] if isinstance(match, tuple) else match.captures
        
        if "function.name" in captures:
            func_name = captures["function.name"][0].text.decode("utf-8")
            func_node = captures["function.def"][0]
            
            parent_class = enclosing_class_name(func_node)
            qual_name = f"{parent_class}.{func_name}" if parent_class else func_name
            
            if qual_name == target_func_name:
                return func_node.text.decode("utf-8")
                
    return f"Error: Function or method '{target_func_name}' not found."
  
IMPORT_QUERY = Query(PY_LANGUAGE, """
(import_statement) @import.std
(import_from_statement) @import.from
""")

def extract_imports(source_bytes: bytes) -> list[str]:
    """Extracts all import statements from a Python source file."""
    tree = parser.parse(source_bytes)
    cursor = QueryCursor(IMPORT_QUERY)
    matches = cursor.matches(tree.root_node)
    
    imports = []
    for pattern_idx, captures in matches:
        for capture_name, nodes in captures.items():
            node = nodes[0] if isinstance(nodes, list) else nodes
            imports.append(source_bytes[node.start_byte:node.end_byte].decode("utf-8").strip())
            
    return list(set(imports))
  
COMPLEXITY_QUERY = Query(PY_LANGUAGE, """
(if_statement) @decision
(for_statement) @decision
(while_statement) @decision
(except_clause) @decision
(with_statement) @decision
(case_clause) @decision
(boolean_operator) @decision
(conditional_expression) @decision
""")