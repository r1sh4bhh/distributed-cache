import unittest
import time
from benchmarks.advanced_benchmark import Benchmark, BenchmarkSuite, StressTester


class TestBenchmark(unittest.TestCase):
    """Test Benchmark class"""
    
    def test_benchmark_creation(self):
        """Test creating a benchmark"""
        def dummy_op():
            pass
        
        bench = Benchmark("Test", dummy_op, 10)
        self.assertEqual(bench.name, "Test")
        self.assertEqual(bench.iterations, 10)
    
    def test_benchmark_run(self):
        """Test running a benchmark"""
        def fast_op():
            time.sleep(0.0001)
        
        bench = Benchmark("Fast", fast_op, 10)
        stats = bench.run()
        
        self.assertEqual(stats['name'], "Fast")
        self.assertEqual(stats['iterations'], 10)
        self.assertGreater(stats['mean'], 0)
    
    def test_percentile_calculation(self):
        """Test percentile calculation"""
        def dummy_op():
            pass
        
        bench = Benchmark("Test", dummy_op, 100)
        bench.times = list(range(100))
        
        p95 = bench._percentile(95)
        self.assertGreaterEqual(p95, 90)


class TestBenchmarkSuite(unittest.TestCase):
    """Test BenchmarkSuite"""
    
    def test_suite_creation(self):
        """Test creating benchmark suite"""
        suite = BenchmarkSuite()
        self.assertEqual(len(suite.benchmarks), 0)
    
    def test_add_benchmark(self):
        """Test adding benchmarks"""
        suite = BenchmarkSuite()
        suite.add_benchmark("Test", lambda: None, 10)
        
        self.assertEqual(len(suite.benchmarks), 1)
    
    def test_connection(self):
        """Test connection (will fail if server not running)"""
        suite = BenchmarkSuite("localhost", 9999)  # Non-existent port
        result = suite.connect()
        self.assertFalse(result)


class TestStressTester(unittest.TestCase):
    """Test StressTester"""
    
    def test_stress_tester_creation(self):
        """Test creating stress tester"""
        tester = StressTester()
        self.assertEqual(tester.results['total_requests'], 0)
        self.assertEqual(tester.results['successful'], 0)


if __name__ == "__main__":
    unittest.main()
