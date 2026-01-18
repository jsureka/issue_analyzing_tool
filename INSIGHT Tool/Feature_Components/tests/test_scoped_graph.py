import unittest
import sys
import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import Feature_Components.KnowledgeBase.language_parser as lp
from Feature_Components.KnowledgeBase.indexer import RepositoryIndexer
from unittest.mock import MagicMock, patch

class TestScopedGraphResolution(unittest.TestCase):
    def setUp(self):
        # Mock dependencies to prevent real connections
        with patch('Feature_Components.KnowledgeBase.indexer.GraphStore'), \
             patch('Feature_Components.KnowledgeBase.indexer.VectorStore'), \
             patch('Feature_Components.KnowledgeBase.indexer.CodeEmbedder'), \
             patch('Feature_Components.KnowledgeBase.indexer.ParserFactory'):
            self.indexer = RepositoryIndexer("bolt://dummy", "user", "pass")
            self.repo_name = "test_repo"

    def test_python_parser_extraction_structure(self):
        """Verify we designed the CallInfo structure correctly"""
        call = lp.CallInfo(name="method", scope="self", args=[])
        self.assertEqual(call.name, "method")
        self.assertEqual(call.scope, "self")

    def test_resolve_local_class_method(self):
        """Test resolving 'self.method()' to method in same class"""
        current_file = "pkg/service.py"
        
        caller = lp.FunctionInfo(name="runner", signature="def runner(self):", start_line=10, end_line=12, 
                            docstring="", class_name="Service", body="", language="python")
        
        target = lp.FunctionInfo(name="helper", signature="def helper(self):", start_line=20, end_line=22, 
                            docstring="", class_name="Service", body="", language="python")
        
        file_info = {
            'functions': [caller, target],
            'imports': [],
            'classes': [] # Simplified
        }
        
        call = lp.CallInfo(name="helper", scope="self")
        
        resolved_id = self.indexer._resolve_call_target(
            self.repo_name, call, current_file, file_info, {current_file: file_info}, caller
        )
        
        # Expected ID format: repo::file::func::line
        expected_id = self.indexer._generate_id(self.repo_name, current_file, "helper", "20")
        self.assertEqual(resolved_id, expected_id)

    def test_resolve_imported_module_function(self):
        """Test resolving 'utils.helper()' where 'import utils' exists"""
        current_file = "pkg/main.py"
        target_file = "pkg/utils.py"
        
        caller = lp.FunctionInfo(name="main_func", start_line=5, end_line=6, class_name=None, 
                              signature="", docstring="", body="", language="python")
        
        # Import utils
        imp = lp.ImportInfo(module_name="pkg.utils", alias="utils")
        current_file_info = {
            'functions': [caller],
            'imports': [imp],
            'classes': []
        }
        
        # Target file has global function 'helper'
        target_func = lp.FunctionInfo(name="helper", start_line=50, end_line=55, class_name=None,
                                 signature="", docstring="", body="", language="python")
        target_file_info = {
            'functions': [target_func],
            'imports': [],
            'classes': []
        }
        
        all_files = {
            current_file: current_file_info,
            target_file: target_file_info
        }
        
        # Caller calls 'utils.helper'
        call = lp.CallInfo(name="helper", scope="utils")
        
        resolved_id = self.indexer._resolve_call_target(
            self.repo_name, call, current_file, current_file_info, all_files, caller
        )
        
        expected_id = self.indexer._generate_id(self.repo_name, target_file, "helper", "50")
        self.assertEqual(resolved_id, expected_id)

    def test_resolve_ignore_ambiguous_global(self):
        """Test that 'print()' (no scope) logic ignores ambiguous matches if not strict (or returns None for external)"""
        current_file = "main.py"
        caller = lp.FunctionInfo(name="foo", start_line=1, end_line=2, class_name=None, signature="", docstring="", body="", language="python")
        
        # No local 'print' function
        current_file_info = {'functions': [caller], 'imports': []}
        
        call = lp.CallInfo(name="print", scope=None)
        
        resolved_id = self.indexer._resolve_call_target(
            self.repo_name, call, current_file, current_file_info, {current_file: current_file_info}, caller
        )
        
        # Should be None because 'print' is not defined in the file
        self.assertIsNone(resolved_id)

    def test_resolve_from_import(self):
        """Test resolving 'helper()' from 'from pkg.utils import helper'"""
        current_file = "main.py"
        target_file = "pkg/utils.py"
        
        caller = lp.FunctionInfo(name="foo", start_line=1, end_line=2, class_name=None, signature="", docstring="", body="", language="python")
        
        # from pkg.utils import helper
        imp = lp.ImportInfo(module_name="pkg.utils", imported_elements=["helper"])
        current_file_info = {'functions': [caller], 'imports': [imp]}
        
        target_func = lp.FunctionInfo(name="helper", start_line=10, end_line=11, class_name=None, signature="", docstring="", body="", language="python")
        target_file_info = {'functions': [target_func], 'imports': []}
        
        all_files = {current_file: current_file_info, target_file: target_file_info}
        
        call = lp.CallInfo(name="helper", scope=None)
        
        resolved_id = self.indexer._resolve_call_target(
             self.repo_name, call, current_file, current_file_info, all_files, caller
        )
        
        expected_id = self.indexer._generate_id(self.repo_name, target_file, "helper", "10")
        self.assertEqual(resolved_id, expected_id)

if __name__ == '__main__':
    unittest.main()
