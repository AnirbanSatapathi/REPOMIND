"""Debug Go parser tree structure."""
from tree_sitter_languages import get_language
from tree_sitter import Parser as TSParser

code = b'package main\nimport "fmt"\ntype Foo struct{}\nfunc main() { fmt.Println("hi") }\n'

p = TSParser()
p.set_language(get_language("go"))
tree = p.parse(code)
root = tree.root_node

def print_tree(node, depth=0):
    indent = "  " * depth
    print(f"{indent}{node.type} [{node.start_byte}:{node.end_byte}] text={code[node.start_byte:node.end_byte]!r}")
    for child in node.children:
        print_tree(child, depth + 1)

print_tree(root)