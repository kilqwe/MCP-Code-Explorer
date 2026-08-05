from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_javascript as tsjavascript
from utils import first_doc_line

JS_LANGUAGE = Language(tsjavascript.language())
parser = Parser(JS_LANGUAGE)


OUTLINE_QUERY = Query(JS_LANGUAGE, """
(function_declaration
  name: (identifier) @func.name
  parameters: (formal_parameters) @func.params
) @func.def

(method_definition
  name: (property_identifier) @func.name
  parameters: (formal_parameters) @func.params
) @func.def

(class_declaration
  name: (identifier) @class.name
) @class.def
""")

def enclosing_class_name(func_def_node, source_bytes):
    """Walk up the JS tree to find the enclosing class."""
    node = func_def_node.parent
    while node is not None:
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
        node = node.parent
    return None