"""
Tests for TelemetryLogger - Performance metrics and system health tracking
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from Feature_Components.KnowledgeBase.telemetry import TelemetryLogger


class TestTelemetryLogger(unittest.TestCase):
    """Test cases for TelemetryLogger"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test logs
        self.temp_dir = tempfile.mkdtemp()
        self.logger = TelemetryLogger(log_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_log_retrieval_success(self):
        """Test logging successful retrieval"""
        self.logger.log_retrieval(
            issue_id="123",
            latency_ms=1500.5,
            top_k=10,
            confidence="high",
            repo_name="test/repo",
            success=True
        )
        
        # Check in-memory metrics
        self.assertEqual(len(self.logger._metrics['retrieval']), 1)
        metric = self.logger._metrics['retrieval'][0]
        
        self.assertEqual(metric['issue_id'], "123")
        self.assertEqual(metric['latency_ms'], 1500.5)
        self.assertEqual(metric['top_k'], 10)
        self.assertEqual(metric['confidence'], "high")
        self.assertEqual(metric['repo_name'], "test/repo")
        self.assertTrue(metric['success'])
    
    def test_log_retrieval_failure(self):
        """Test logging failed retrieval"""
        self.logger.log_retrieval(
            issue_id="456",
            latency_ms=500.0,
            top_k=0,
            confidence="low",
            repo_name="test/repo",
            success=False
        )
        
        metric = self.logger._metrics['retrieval'][0]
        self.assertFalse(metric['success'])
        self.assertEqual(metric['top_k'], 0)
    
    def test_log_indexing_success(self):
        """Test logging successful indexing"""
        self.logger.log_indexing(
            repo_name="test/repo",
            files_indexed=100,
            duration_seconds=45.5,
            functions_count=500,
            success=True
        )
        
        self.assertEqual(len(self.logger._metrics['indexing']), 1)
        metric = self.logger._metrics['indexing'][0]
        
        self.assertEqual(metric['repo_name'], "test/repo")
        self.assertEqual(metric['files_indexed'], 100)
        self.assertEqual(metric['duration_seconds'], 45.5)
        self.assertEqual(metric['functions_count'], 500)
        self.assertTrue(metric['success'])
    
    def test_log_indexing_failure(self):
        """Test logging failed indexing"""
        self.logger.log_indexing(
            repo_name="test/repo",
            files_indexed=50,
            duration_seconds=10.0,
            success=False,
            error_msg="Parse error"
        )
        
        metric = self.logger._metrics['indexing'][0]
        self.assertFalse(metric['success'])
        self.assertEqual(metric['error_msg'], "Parse error")
    
    def test_log_error(self):
        """Test error logging with context"""
        self.logger.log_error(
            error_type="retrieval_failed",
            error_msg="Index not found",
            context={'issue_id': '789', 'repo': 'test/repo'}
        )
        
        self.assertEqual(len(self.logger._metrics['errors']), 1)
        metric = self.logger._metrics['errors'][0]
        
        self.assertEqual(metric['error_type'], "retrieval_failed")
        self.assertEqual(metric['error_msg'], "Index not found")
        self.assertEqual(metric['context']['issue_id'], '789')
    
    def test_json_log_file_written(self):
        """Test that metrics are written to JSON log file"""
        self.logger.log_retrieval(
            issue_id="test",
            latency_ms=1000.0,
            top_k=5,
            confidence="medium",
            repo_name="test/repo"
        )
        
        # Check log file exists
        log_file = self.logger.log_file
        self.assertTrue(log_file.exists())
        
        # Read and verify JSON content
        with open(log_file, 'r') as f:
            line = f.readline()
            data = json.loads(line)
            
            self.assertEqual(data['type'], 'retrieval')
            self.assertEqual(data['issue_id'], 'test')
            self.assertEqual(data['latency_ms'], 1000.0)
    
    def test_statistics_retrieval(self):
        """Test aggregate statistics computation for retrievals"""
        # Log multiple retrievals
        for i in range(10):
            self.logger.log_retrieval(
                issue_id=str(i),
                latency_ms=1000.0 + (i * 100),
                top_k=10,
                confidence="high" if i < 5 else "medium",
                repo_name="test/repo",
                success=True
            )
        
        # Get statistics
        stats = self.logger.get_statistics("24h")
        
        self.assertIn('retrieval', stats)
        retrieval_stats = stats['retrieval']
        
        self.assertEqual(retrieval_stats['total_requests'], 10)
        self.assertEqual(retrieval_stats['successful_requests'], 10)
        self.assertEqual(retrieval_stats['success_rate'], 1.0)
        self.assertGreater(retrieval_stats['avg_latency_ms'], 0)
        
        # Check confidence distribution
        conf_dist = retrieval_stats['confidence_distribution']
        self.assertEqual(conf_dist['high'], 5)
        self.assertEqual(conf_dist['medium'], 5)
    
    def test_statistics_indexing(self):
        """Test aggregate statistics computation for indexing"""
        # Log multiple indexing operations
        self.logger.log_indexing("repo1", 100, 30.0, 500, True)
        self.logger.log_indexing("repo2", 200, 60.0, 1000, True)
        self.logger.log_indexing("repo3", 50, 15.0, 250, False, "Error")
        
        stats = self.logger.get_statistics("24h")
        
        self.assertIn('indexing', stats)
        indexing_stats = stats['indexing']
        
        self.assertEqual(indexing_stats['total_operations'], 3)
        self.assertEqual(indexing_stats['successful_operations'], 2)
        self.assertAlmostEqual(indexing_stats['success_rate'], 2/3, places=2)
        self.assertEqual(indexing_stats['total_files_indexed'], 300)
        self.assertEqual(indexing_stats['total_functions_indexed'], 1500)
    
    def test_statistics_errors(self):
        """Test error statistics computation"""
        # Log multiple errors
        self.logger.log_error("retrieval_failed", "Error 1")
        self.logger.log_error("retrieval_failed", "Error 2")
        self.logger.log_error("indexing_failed", "Error 3")
        
        stats = self.logger.get_statistics("24h")
        
        self.assertIn('errors', stats)
        error_stats = stats['errors']
        
        self.assertEqual(error_stats['total_errors'], 3)
        self.assertEqual(error_stats['error_types']['retrieval_failed'], 2)
        self.assertEqual(error_stats['error_types']['indexing_failed'], 1)
    
    def test_time_range_parsing(self):
        """Test time range string parsing"""
        now = datetime.utcnow()
        
        # Test hours
        cutoff_1h = self.logger._parse_time_range("1h")
        self.assertAlmostEqual(
            (now - cutoff_1h).total_seconds(), 
            3600, 
            delta=1
        )
        
        # Test days
        cutoff_7d = self.logger._parse_time_range("7d")
        self.assertAlmostEqual(
            (now - cutoff_7d).total_seconds(), 
            7 * 24 * 3600, 
            delta=1
        )
        
        # Test minutes
        cutoff_30m = self.logger._parse_time_range("30m")
        self.assertAlmostEqual(
            (now - cutoff_30m).total_seconds(), 
            30 * 60, 
            delta=1
        )
    
    def test_memory_limit(self):
        """Test that in-memory metrics are limited to 1000 entries"""
        # Log more than 1000 retrievals
        for i in range(1500):
            self.logger.log_retrieval(
                issue_id=str(i),
                latency_ms=1000.0,
                top_k=10,
                confidence="high",
                repo_name="test/repo"
            )
        
        # Check that only last 1000 are kept
        self.assertEqual(len(self.logger._metrics['retrieval']), 1000)
        
        # Verify it's the most recent ones
        first_metric = self.logger._metrics['retrieval'][0]
        self.assertEqual(first_metric['issue_id'], "500")
    
    def test_thread_safety(self):
        """Test thread-safe metric logging"""
        import threading
        
        def log_metrics(thread_id):
            for i in range(100):
                self.logger.log_retrieval(
                    issue_id=f"{thread_id}-{i}",
                    latency_ms=1000.0,
                    top_k=10,
                    confidence="high",
                    repo_name="test/repo"
                )
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=log_metrics, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check total count
        self.assertEqual(len(self.logger._metrics['retrieval']), 500)


if __name__ == '__main__':
    unittest.main()
