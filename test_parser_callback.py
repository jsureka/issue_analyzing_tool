"""Test tree-sitter parser with callback"""
import tree_sitter_java as tsjava
from tree_sitter import Parser

# Initialize parser
parser = Parser(tsjava.language())
print("Parser initialized")

# Read Java file
with open("WheelOfFortune-master/Wheel.java", 'rb') as f:
    source_code = f.read()

print(f"Source code length: {len(source_code)} bytes")

# Try different parse methods
print("\nMethod 1: parse(source_code)")
try:
    tree = parser.parse(source_code)
    print(f"Success! Tree: {tree}")
except Exception as e:
    print(f"Failed: {e}")

print("\nMethod 2: parse(source_code, keep_text=True)")
try:
    tree = parser.parse(source_code, keep_text=True)
    print(f"Success! Tree: {tree}")
except Exception as e:
    print(f"Failed: {e}")

print("\nMethod 3: parse with read callback")
try:
    def read_callable(byte_offset, point):
        return source_code[byte_offset:byte_offset+1024]
    
    tree = parser.parse(read_callable)
    print(f"Success! Tree: {tree}")
except Exception as e:
    print(f"Failed: {e}")

print("\nMethod 4: parse with lambda")
try:
    tree = parser.parse(lambda offset, point: source_code[offset:offset+1024])
    print(f"Success! Tree: {tree}")
    if tree:
        print(f"Root node type: {tree.root_node.type}")
except Exception as e:
    print(f"Failed: {e}")
