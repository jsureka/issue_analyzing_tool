"""Test tree-sitter parser API"""
import tree_sitter_java as tsjava
from tree_sitter import Parser

# Initialize parser
parser = Parser(tsjava.language())
print("Parser initialized")

# Read Java file
with open("WheelOfFortune-master/Wheel.java", 'rb') as f:
    source_code = f.read()

print(f"Source code length: {len(source_code)} bytes")

# Try to parse
try:
    tree = parser.parse(source_code)
    print(f"Parse successful!")
    print(f"Tree: {tree}")
    print(f"Root node: {tree.root_node}")
    print(f"Root node type: {tree.root_node.type}")
    print(f"Has error: {tree.root_node.has_error}")
    
    # Print first few children
    print(f"\nFirst 5 children:")
    for i, child in enumerate(tree.root_node.children[:5]):
        print(f"  {i}. {child.type} ({child.start_point} - {child.end_point})")
        
except Exception as e:
    print(f"Parse failed: {e}")
    import traceback
    traceback.print_exc()
