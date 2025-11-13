"""Debug Java parser"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SPRINT Tool'))

from Feature_Components.KnowledgeBase.java_parser import JavaParser

parser = JavaParser()
print("Parser initialized successfully")

# Test parsing a simple Java file
java_file = "WheelOfFortune-master/Wheel.java"
print(f"\nParsing {java_file}...")

tree = parser.parse_file(java_file)
print(f"Tree: {tree}")
print(f"Tree type: {type(tree)}")

if tree:
    print(f"Root node: {tree.root_node}")
    print(f"Root node type: {tree.root_node.type}")
    print(f"Has error: {tree.root_node.has_error}")
    
    # Try to extract functions
    with open(java_file, 'rb') as f:
        source_code = f.read()
    
    functions = parser.extract_functions(tree, source_code, java_file)
    print(f"\nExtracted {len(functions)} functions:")
    for func in functions[:5]:
        print(f"  - {func.name} ({func.start_line}-{func.end_line})")
else:
    print("Failed to parse!")
