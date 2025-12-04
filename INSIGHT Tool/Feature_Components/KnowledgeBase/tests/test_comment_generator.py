"""
Tests for CommentGenerator - GitHub comment generation
"""

import unittest
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator


class TestCommentGenerator(unittest.TestCase):
    """Test cases for CommentGenerator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.generator = CommentGenerator("test-owner", "test-repo")
        
        # Sample retrieval results
        self.sample_results = {
            'repository': 'test-owner/test-repo',
            'commit_sha': 'abc123def456',
            'timestamp': '2025-11-13T12:00:00Z',
            'total_results': 5,
            'top_files': [
                {
                    'file_path': 'src/module/processor.py',
                    'score': 0.87,
                    'functions': [
                        {
                            'name': 'process_data',
                            'signature': 'def process_data(input: str) -> dict:',
                            'line_range': [45, 78],
                            'score': 0.87,
                            'snippet': 'def process_data(input: str) -> dict:\n    result = {}\n    return result',
                            'class_name': None,
                            'docstring': 'Process input data'
                        }
                    ]
                },
                {
                    'file_path': 'src/module/validator.py',
                    'score': 0.76,
                    'functions': [
                        {
                            'name': 'validate_input',
                            'signature': 'def validate_input(data: str) -> bool:',
                            'line_range': [23, 35],
                            'score': 0.76,
                            'snippet': 'def validate_input(data: str) -> bool:\n    return True',
                            'class_name': None,
                            'docstring': 'Validate input data'
                        }
                    ]
                }
            ]
        }
    

    
    def test_github_permalink_generation(self):
        """Test GitHub permalink URL generation"""
        permalink = self.generator._generate_github_permalink(
            "src/test.py", 10, 20, "abc123"
        )
        
        expected = "https://github.com/test-owner/test-repo/blob/abc123/src/test.py#L10-L20"
        self.assertEqual(permalink, expected)
    
    def test_github_permalink_single_line(self):
        """Test GitHub permalink for single line"""
        permalink = self.generator._generate_github_permalink(
            "src/test.py", 15, 15, "abc123"
        )
        
        expected = "https://github.com/test-owner/test-repo/blob/abc123/src/test.py#L15"
        self.assertEqual(permalink, expected)
    
    def test_code_snippet_formatting(self):
        """Test code snippet markdown formatting"""
        code = "def test():\n    return True"
        formatted = self.generator._format_code_snippet(code, "python")
        
        self.assertIn("```python", formatted)
        self.assertIn("def test():", formatted)
        self.assertIn("```", formatted)
    
    def test_code_snippet_with_highlights(self):
        """Test code snippet with line highlights"""
        code = "line1\nline2\nline3"
        formatted = self.generator._format_code_snippet(
            code, "python", highlight_lines=[2], start_line=10
        )
        
        self.assertIn("⚠️", formatted)
        self.assertIn("Line 11", formatted)  # start_line=10, so line 2 is 11
    
    def test_generate_comment_structure(self):
        """Test complete comment generation structure"""
        comment = self.generator.generate_comment(
            self.sample_results, 
            confidence="high", 
            confidence_score=0.92
        )
        
        # Check main sections
        self.assertIn("🔍 Bug Localization Results", comment)
        self.assertIn("Confidence:", comment)
        self.assertIn("Top Candidate Functions", comment)
        self.assertIn("Summary", comment)
        
        # Check confidence
        self.assertIn("High", comment)
        self.assertIn("92%", comment)
        self.assertIn("🟢", comment)
        
        # Check function details
        self.assertIn("process_data", comment)
        self.assertIn("src/module/processor.py", comment)
        self.assertIn("Lines 45-78", comment)
        
        # Check permalink
        self.assertIn("View on GitHub", comment)
        self.assertIn("https://github.com/test-owner/test-repo/blob/abc123", comment)
        
        # Check code snippet
        self.assertIn("```python", comment)
        self.assertIn("def process_data", comment)
        
        # Check summary
        self.assertIn("Total functions analyzed:", comment)
        self.assertIn("5", comment)
        self.assertIn("abc123", comment)
        
        # Check label
        self.assertIn("bug-localization:high-confidence", comment)
    
    def test_generate_comment_limits_functions(self):
        """Test that comment limits to top 5 functions"""
        # Create results with many functions
        many_functions = {
            'repository': 'test/repo',
            'commit_sha': 'abc123',
            'timestamp': '2025-11-13T12:00:00Z',
            'total_results': 20,
            'top_files': []
        }
        
        # Add 10 files with 2 functions each
        for i in range(10):
            many_functions['top_files'].append({
                'file_path': f'file{i}.py',
                'score': 0.9 - (i * 0.05),
                'functions': [
                    {
                        'name': f'func{i}_1',
                        'signature': f'def func{i}_1():',
                        'line_range': [1, 10],
                        'score': 0.9 - (i * 0.05),
                        'snippet': 'def test(): pass'
                    },
                    {
                        'name': f'func{i}_2',
                        'signature': f'def func{i}_2():',
                        'line_range': [11, 20],
                        'score': 0.85 - (i * 0.05),
                        'snippet': 'def test2(): pass'
                    }
                ]
            })
        
        comment = self.generator.generate_comment(many_functions, "medium", 0.7)
        
        # Count function sections (should be max 5)
        function_count = comment.count("#### ")
        self.assertLessEqual(function_count, 5)
    
    def test_generate_error_comment(self):
        """Test error comment generation"""
        error_comment = self.generator._generate_error_comment("Test error message")
        
        self.assertIn("🔍 Bug Localization Results", error_comment)
        self.assertIn("⚠️", error_comment)
        self.assertIn("Error", error_comment)
        self.assertIn("Test error message", error_comment)
    
    def test_empty_results(self):
        """Test comment generation with empty results"""
        empty_results = {
            'repository': 'test/repo',
            'commit_sha': 'abc123',
            'timestamp': '2025-11-13T12:00:00Z',
            'total_results': 0,
            'top_files': []
        }
        
        comment = self.generator.generate_comment(empty_results, "low", 0.2)
        
        # Should still generate valid comment structure
        self.assertIn("🔍 Bug Localization Results", comment)
        self.assertIn("Low", comment)
        self.assertIn("Summary", comment)


if __name__ == '__main__':
    unittest.main()
