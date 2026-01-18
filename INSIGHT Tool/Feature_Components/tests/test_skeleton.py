import sys
import os
import unittest
from dataclasses import dataclass
from typing import List, Optional

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import dataclasses from language_parser (mocking if import fails, but should work)
try:
    from Feature_Components.KnowledgeBase.language_parser import FunctionInfo, ClassInfo
except ImportError:
    # Fallback mock if environment issue
    @dataclass
    class FunctionInfo:
        name: str
        signature: str
        start_line: int
        end_line: int
        docstring: Optional[str]
        class_name: Optional[str]
        body: str
        language: str = "python"

    @dataclass
    class ClassInfo:
        name: str
        start_line: int
        end_line: int
        functions: List[str]
        language: str = "python"
        docstring: Optional[str] = None

from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer

class TestSkeleton(unittest.TestCase):
    def setUp(self):
        # Initialize with dummy values (dependencies shouldn't connect/load on init)
        try:
            self.indexer = RepositoryIndexer("bolt://localhost:7687", "neo4j", "password")
        except Exception as e:
            print(f"Failed to init indexer (might be dependency issue): {e}")
            self.skipTest("Indexer init failed")

    def test_class_skeleton(self):
        # Mock class and methods
        cls = ClassInfo(
            name="TestClass",
            start_line=1,
            end_line=10,
            functions=["__init__", "method1"],
            docstring="A test class"
        )
        
        methods = [
            FunctionInfo(
                name="__init__",
                signature="def __init__(self):",
                start_line=2,
                end_line=4,
                docstring=None,
                class_name="TestClass",
                body="def __init__(self):\n    self.x = 1"
            ),
            FunctionInfo(
                name="method1",
                signature="def method1(self):",
                start_line=6,
                end_line=8,
                docstring="Doc",
                class_name="TestClass",
                body="def method1(self):\n    pass"
            )
        ]
        
        skeleton = self.indexer._create_class_skeleton(cls, methods)
        print("\n--- Class Skeleton ---")
        print(skeleton)
        print("----------------------")
        
        self.assertIn("class TestClass:", skeleton)
        self.assertIn('"""A test class"""', skeleton)
        self.assertIn("self.x = 1", skeleton, "Should keep __init__ body")
        self.assertIn("def method1(self):", skeleton)
        self.assertIn("... # Body masked", skeleton)
        self.assertNotIn("pass", skeleton, "Should mask method1 body")

    def test_file_skeleton(self):
        code = """import os

def top_level():
    print("Mask me")
    return True

class TopClass:
    def method(self):
        pass

# Global logic
if __name__ == "__main__":
    main()
"""
        # Mock extracted info (indices are 1-based)
        functions = [
            FunctionInfo(
                name="top_level",
                signature="def top_level():",
                start_line=3,
                # lines 0: import, 1: blank, 2: def top... (start_line=3 if 1-based)
                end_line=5,
                docstring=None,
                class_name=None,
                body="..."
            )
        ]
        
        classes = [
            ClassInfo(
                name="TopClass",
                start_line=7,
                end_line=9,
                functions=["method"],
                docstring=None
            )
        ]
        
        skeleton = self.indexer._create_file_skeleton(code, functions, classes)
        print("\n--- File Skeleton ---")
        print(skeleton)
        print("---------------------")
        
        self.assertIn("import os", skeleton)
        self.assertIn("def top_level():", skeleton) # Signature kept (line 3)
        self.assertIn("... # Body masked", skeleton)
        self.assertNotIn('print("Mask me")', skeleton, "Should mask function body")
        
        self.assertIn("class TopClass:", skeleton)
        self.assertNotIn("def method(self):", skeleton, "Should mask class content entirely in file node")
        
        self.assertIn('if __name__ == "__main__":', skeleton, "Should keep global logic")

if __name__ == '__main__':
    unittest.main()
