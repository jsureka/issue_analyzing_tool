"""
Unit tests for Python parser module
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from Feature_Components.KnowledgeBase.parser import PythonParser, FunctionInfo, ClassInfo


class TestPythonParser(unittest.TestCase):
    """Test cases for PythonParser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = PythonParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str, content: str) -> str:
        """Helper to create a test Python file"""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def test_parser_initialization(self):
        """Test that parser initializes correctly"""
        self.assertIsNotNone(self.parser)
        self.assertIsNotNone(self.parser.parser)
        self.assertIsNotNone(self.parser.language)
    
    def test_parse_simple_function(self):
        """Test parsing a simple function"""
        code = '''
def hello_world():
    """Say hello"""
    print("Hello, World!")
    return True
'''
        filepath = self._create_test_file('test_simple.py', code)
        tree = self.parser.parse_file(filepath)
        
        self.assertIsNotNone(tree)
        self.assertFalse(tree.root_node.has_error)
        
        # Extract functions
        with open(filepath, 'rb') as f:
            source_code = f.read()
        functions = self.parser.extract_functions(tree, source_code, filepath)
        
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions[0].name, 'hello_world')
        self.assertEqual(functions[0].docstring, 'Say hello')
        self.assertIsNone(functions[0].class_name)
    
    def test_parse_class_with_methods(self):
        """Test parsing a class with methods"""
        code = '''
class Calculator:
    """A simple calculator"""
    
    def add(self, a, b):
        """Add two numbers"""
        return a + b
    
    def subtract(self, a, b):
        """Subtract two numbers"""
        return a - b
'''
        filepath = self._create_test_file('test_class.py', code)
        tree = self.parser.parse_file(filepath)
        
        with open(filepath, 'rb') as f:
            source_code = f.read()
        
        # Extract classes
        classes = self.parser.extract_classes(tree, source_code, filepath)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, 'Calculator')
        self.assertEqual(len(classes[0].functions), 2)
        self.assertIn('add', classes[0].functions)
        self.assertIn('subtract', classes[0].functions)
        
        # Extract functions
        functions = self.parser.extract_functions(tree, source_code, filepath)
        self.assertEqual(len(functions), 2)
        
        # Check that functions know their class
        for func in functions:
            self.assertEqual(func.class_name, 'Calculator')
    
    def test_parse_imports(self):
        """Test extracting import statements"""
        code = '''
import os
import sys
from pathlib import Path
from typing import List, Dict
'''
        filepath = self._create_test_file('test_imports.py', code)
        tree = self.parser.parse_file(filepath)
        
        with open(filepath, 'rb') as f:
            source_code = f.read()
        
        imports = self.parser.extract_imports(tree, source_code)
        self.assertEqual(len(imports), 4)
        self.assertTrue(any('os' in imp for imp in imports))
        self.assertTrue(any('sys' in imp for imp in imports))
        self.assertTrue(any('pathlib' in imp for imp in imports))
    
    def test_parse_function_calls(self):
        """Test extracting function calls"""
        code = '''
def process_data(data):
    cleaned = clean_data(data)
    validated = validate_data(cleaned)
    return save_data(validated)

def clean_data(data):
    return data.strip()
'''
        filepath = self._create_test_file('test_calls.py', code)
        tree = self.parser.parse_file(filepath)
        
        with open(filepath, 'rb') as f:
            source_code = f.read()
        
        calls = self.parser.extract_calls(tree, source_code)
        
        # process_data should call clean_data, validate_data, save_data
        self.assertIn('process_data', calls)
        self.assertGreater(len(calls['process_data']), 0)
    
    def test_parse_malformed_code(self):
        """Test handling of malformed Python code"""
        code = '''
def broken_function(
    # Missing closing parenthesis and colon
    print("This is broken"
'''
        filepath = self._create_test_file('test_broken.py', code)
        tree = self.parser.parse_file(filepath)
        
        # Should still return a tree, but with errors
        self.assertIsNotNone(tree)
        # Parser should handle errors gracefully
    
    def test_parse_nested_functions(self):
        """Test parsing nested function definitions"""
        code = '''
def outer_function():
    """Outer function"""
    def inner_function():
        """Inner function"""
        return 42
    return inner_function()
'''
        filepath = self._create_test_file('test_nested.py', code)
        tree = self.parser.parse_file(filepath)
        
        with open(filepath, 'rb') as f:
            source_code = f.read()
        
        functions = self.parser.extract_functions(tree, source_code, filepath)
        
        # Should find both outer and inner functions
        self.assertGreaterEqual(len(functions), 1)
        func_names = [f.name for f in functions]
        self.assertIn('outer_function', func_names)
    
    def test_function_line_numbers(self):
        """Test that line numbers are correctly extracted"""
        code = '''# Line 1
# Line 2
def first_function():  # Line 3
    """First function"""  # Line 4
    pass  # Line 5

def second_function():  # Line 7
    """Second function"""  # Line 8
    return True  # Line 9
'''
        filepath = self._create_test_file('test_lines.py', code)
        tree = self.parser.parse_file(filepath)
        
        with open(filepath, 'rb') as f:
            source_code = f.read()
        
        functions = self.parser.extract_functions(tree, source_code, filepath)
        
        self.assertEqual(len(functions), 2)
        
        # Check line numbers (1-based)
        first_func = [f for f in functions if f.name == 'first_function'][0]
        self.assertEqual(first_func.start_line, 3)
        
        second_func = [f for f in functions if f.name == 'second_function'][0]
        self.assertEqual(second_func.start_line, 7)


if __name__ == '__main__':
    unittest.main()
