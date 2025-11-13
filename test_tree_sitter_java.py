"""Quick test to check tree-sitter-java API"""
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

print("Testing tree-sitter-java API...")
print(f"tsjava.language() type: {type(tsjava.language())}")
print(f"tsjava.language(): {tsjava.language()}")

# Try different initialization methods
try:
    print("\nMethod 1: Language(tsjava.language(), 'java')")
    lang = Language(tsjava.language(), "java")
    print(f"Success! Type: {type(lang)}")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nMethod 2: Language(tsjava.language())")
    lang = Language(tsjava.language())
    print(f"Success! Type: {type(lang)}")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nMethod 3: Direct use of tsjava.language()")
    parser = Parser()
    parser.set_language(tsjava.language())
    print(f"Success!")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nMethod 4: Parser(tsjava.language())")
    parser = Parser(tsjava.language())
    print(f"Success!")
except Exception as e:
    print(f"Failed: {e}")
