"""
Test runner for Knowledge Base System
Run all tests or specific test suites
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def run_all_tests():
    """Run all test suites"""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_unit_tests():
    """Run only unit tests (fast)"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add specific test modules
    from test_parser import TestPythonParser
    from test_vector_store import TestVectorStore
    
    suite.addTests(loader.loadTestsFromTestCase(TestPythonParser))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorStore))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_integration_tests():
    """Run integration tests (requires Neo4j)"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    from test_integration import TestIntegration
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_performance_tests():
    """Run performance benchmarks"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    from test_performance import TestPerformance
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Knowledge Base tests')
    parser.add_argument('suite', nargs='?', default='all',
                       choices=['all', 'unit', 'integration', 'performance'],
                       help='Test suite to run')
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"Running {args.suite.upper()} tests for Knowledge Base System")
    print(f"{'='*70}\n")
    
    if args.suite == 'all':
        success = run_all_tests()
    elif args.suite == 'unit':
        success = run_unit_tests()
    elif args.suite == 'integration':
        success = run_integration_tests()
    elif args.suite == 'performance':
        success = run_performance_tests()
    
    sys.exit(0 if success else 1)
