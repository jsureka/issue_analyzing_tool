"""
Phase 2 Integration Tests - End-to-end SPRINT workflow testing
"""

import unittest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock
from Feature_Components.KnowledgeBase.comment_generator import CommentGenerator
from Feature_Components.KnowledgeBase.telemetry import TelemetryLogger


class TestPhase2Integration(unittest.TestCase):
    """Integration tests for Phase 2 SPRINT workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Sample issue data
        self.test_issue = {
            'issue_number': 123,
            'issue_title': 'Bug in data processing',
            'issue_body': 'The process_data function crashes when input is empty',
            'issue_branch': 'main',
            'created_at': '2025-11-13T12:00:00Z',
            'issue_url': 'https://github.com/test/repo/issues/123',
            'issue_labels': []
        }
        
        # Sample KB results
        self.kb_results = {
            'repository': 'test-owner/test-repo',
            'commit_sha': 'abc123def456',
            'timestamp': '2025-11-13T12:00:00Z',
            'total_results': 3,
            'confidence': 'high',
            'confidence_score': 0.92,
            'top_files': [
                {
                    'file_path': 'src/processor.py',
                    'score': 0.87,
                    'functions': [
                        {
                            'name': 'process_data',
                            'signature': 'def process_data(input: str) -> dict:',
                            'line_range': [45, 78],
                            'score': 0.87,
                            'snippet': 'def process_data(input: str) -> dict:\n    if not input:\n        raise ValueError("Empty input")\n    return {}',
                            'class_name': None,
                            'docstring': 'Process input data'
                        }
                    ]
                }
            ]
        }
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_comment_generation_workflow(self):
        """Test complete comment generation workflow"""
        # Create comment generator
        generator = CommentGenerator("test-owner", "test-repo")
        
        # Generate comment
        comment = generator.generate_comment(
            self.kb_results,
            confidence="high",
            confidence_score=0.92
        )
        
        # Verify comment structure
        self.assertIsInstance(comment, str)
        self.assertGreater(len(comment), 100)
        
        # Verify key elements
        self.assertIn("🔍 Bug Localization Results", comment)
        self.assertIn("High", comment)
        self.assertIn("92%", comment)
        self.assertIn("process_data", comment)
        self.assertIn("src/processor.py", comment)
        self.assertIn("View on GitHub", comment)
        self.assertIn("```python", comment)
        self.assertIn("bug-localization:high-confidence", comment)
    
    def test_telemetry_logging_workflow(self):
        """Test telemetry logging during retrieval"""
        telemetry = TelemetryLogger(log_path=self.temp_dir)
        
        # Simulate retrieval
        start_time = time.time()
        time.sleep(0.1)  # Simulate processing
        latency_ms = (time.time() - start_time) * 1000
        
        # Log retrieval
        telemetry.log_retrieval(
            issue_id=str(self.test_issue['issue_number']),
            latency_ms=latency_ms,
            top_k=3,
            confidence="high",
            repo_name="test-owner/test-repo",
            success=True
        )
        
        # Verify logging
        self.assertEqual(len(telemetry._metrics['retrieval']), 1)
        
        # Get statistics
        stats = telemetry.get_statistics("1h")
        self.assertEqual(stats['retrieval']['total_requests'], 1)
        self.assertEqual(stats['retrieval']['success_rate'], 1.0)
        self.assertGreater(stats['retrieval']['avg_latency_ms'], 0)
    
    def test_end_to_end_latency_under_threshold(self):
        """Test that end-to-end processing completes within 10 seconds"""
        start_time = time.time()
        
        # Simulate workflow steps
        # 1. Comment generation
        generator = CommentGenerator("test-owner", "test-repo")
        comment = generator.generate_comment(
            self.kb_results,
            confidence="high",
            confidence_score=0.92
        )
        
        # 2. Telemetry logging
        telemetry = TelemetryLogger(log_path=self.temp_dir)
        telemetry.log_retrieval(
            issue_id="123",
            latency_ms=1500.0,
            top_k=3,
            confidence="high",
            repo_name="test/repo"
        )
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Verify under threshold (should be much faster than 10s)
        self.assertLess(total_time, 10.0)
        print(f"End-to-end processing time: {total_time:.3f}s")
    
    def test_error_handling_and_logging(self):
        """Test error handling and telemetry logging"""
        telemetry = TelemetryLogger(log_path=self.temp_dir)
        
        # Simulate failed retrieval
        telemetry.log_retrieval(
            issue_id="456",
            latency_ms=500.0,
            top_k=0,
            confidence="low",
            repo_name="test/repo",
            success=False
        )
        
        # Log error
        telemetry.log_error(
            error_type="retrieval_failed",
            error_msg="Repository not indexed",
            context={'issue_id': '456', 'repo': 'test/repo'}
        )
        
        # Verify error logged
        self.assertEqual(len(telemetry._metrics['errors']), 1)
        
        # Get statistics
        stats = telemetry.get_statistics("1h")
        self.assertEqual(stats['retrieval']['success_rate'], 0.0)
        self.assertEqual(stats['errors']['total_errors'], 1)
    
    def test_multiple_confidence_levels(self):
        """Test comment generation with different confidence levels"""
        generator = CommentGenerator("test-owner", "test-repo")
        
        # Test high confidence
        comment_high = generator.generate_comment(
            self.kb_results, "high", 0.92
        )
        self.assertIn("🟢", comment_high)
        self.assertIn("bug-localization:high-confidence", comment_high)
        
        # Test medium confidence
        comment_medium = generator.generate_comment(
            self.kb_results, "medium", 0.65
        )
        self.assertIn("🟡", comment_medium)
        self.assertIn("bug-localization:medium-confidence", comment_medium)
        
        # Test low confidence
        comment_low = generator.generate_comment(
            self.kb_results, "low", 0.35
        )
        self.assertIn("🔴", comment_low)
        self.assertIn("bug-localization:low-confidence", comment_low)
    
    def test_empty_results_handling(self):
        """Test handling of empty retrieval results"""
        empty_results = {
            'repository': 'test/repo',
            'commit_sha': 'abc123',
            'timestamp': '2025-11-13T12:00:00Z',
            'total_results': 0,
            'top_files': []
        }
        
        generator = CommentGenerator("test-owner", "test-repo")
        comment = generator.generate_comment(empty_results, "low", 0.1)
        
        # Should still generate valid comment
        self.assertIn("🔍 Bug Localization Results", comment)
        self.assertIn("Summary", comment)
        self.assertIn("0", comment)  # Total results
    
    def test_permalink_generation_accuracy(self):
        """Test that GitHub permalinks are correctly formatted"""
        generator = CommentGenerator("test-owner", "test-repo")
        comment = generator.generate_comment(
            self.kb_results, "high", 0.92
        )
        
        # Check permalink format
        expected_url = "https://github.com/test-owner/test-repo/blob/abc123def456/src/processor.py#L45-L78"
        self.assertIn(expected_url, comment)
    
    def test_concurrent_telemetry_logging(self):
        """Test telemetry logging with concurrent requests"""
        import threading
        
        telemetry = TelemetryLogger(log_path=self.temp_dir)
        
        def log_request(thread_id):
            for i in range(10):
                telemetry.log_retrieval(
                    issue_id=f"{thread_id}-{i}",
                    latency_ms=1000.0 + (i * 10),
                    top_k=5,
                    confidence="medium",
                    repo_name="test/repo"
                )
        
        # Create threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=log_request, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify all logged
        self.assertEqual(len(telemetry._metrics['retrieval']), 30)
        
        # Verify statistics
        stats = telemetry.get_statistics("1h")
        self.assertEqual(stats['retrieval']['total_requests'], 30)
    
    def test_latency_threshold_detection(self):
        """Test detection of latency threshold violations"""
        telemetry = TelemetryLogger(log_path=self.temp_dir)
        
        # Log slow retrieval (> 10 seconds)
        slow_latency_ms = 12000.0  # 12 seconds
        
        telemetry.log_retrieval(
            issue_id="slow-issue",
            latency_ms=slow_latency_ms,
            top_k=5,
            confidence="medium",
            repo_name="test/repo"
        )
        
        # Check if we can detect slow requests
        stats = telemetry.get_statistics("1h")
        avg_latency = stats['retrieval']['avg_latency_ms']
        
        self.assertGreater(avg_latency, 10000.0)  # Should be > 10 seconds


if __name__ == '__main__':
    unittest.main()
