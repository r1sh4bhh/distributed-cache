"""
Comprehensive benchmarking suite for distributed cache
Compare performance against Redis
"""

import time
import statistics
import socket
import threading
from typing import List, Tuple, Dict, Any


class Benchmark:
    """Single benchmark test"""
    
    def __init__(self, name: str, operation: callable, iterations: int = 1000):
        self.name = name
        self.operation = operation
        self.iterations = iterations
        self.times: List[float] = []
        self.errors = 0
    
    def run(self) -> Dict[str, Any]:
        """Run benchmark and collect metrics"""
        self.times.clear()
        self.errors = 0
        
        for _ in range(self.iterations):
            start = time.perf_counter()
            try:
                self.operation()
            except Exception as e:
                self.errors += 1
            end = time.perf_counter()
            
            elapsed = (end - start) * 1000000  # Convert to microseconds
            self.times.append(elapsed)
        
        return self.get_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get benchmark statistics"""
        if not self.times:
            return {}
        
        return {
            "name": self.name,
            "iterations": self.iterations,
            "errors": self.errors,
            "min": min(self.times),
            "max": max(self.times),
            "mean": statistics.mean(self.times),
            "median": statistics.median(self.times),
            "stdev": statistics.stdev(self.times) if len(self.times) > 1 else 0,
            "p95": self._percentile(95),
            "p99": self._percentile(99),
            "total_time_ms": sum(self.times) / 1000,
            "throughput": (self.iterations - self.errors) / (sum(self.times) / 1000000)
        }
    
    def _percentile(self, p: int) -> float:
        """Calculate percentile"""
        sorted_times = sorted(self.times)
        index = int((p / 100) * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]


class BenchmarkSuite:
    """Suite of benchmarks"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.socket = None
        self.benchmarks: List[Benchmark] = []
        self.results: List[Dict[str, Any]] = []
    
    def connect(self) -> bool:
        """Connect to cache server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def _send_command(self, *args) -> Any:
        """Send RESP command and receive response"""
        # Build RESP request
        cmd_bytes = f"*{len(args)}\r\n".encode()
        for arg in args:
            arg_str = str(arg)
            cmd_bytes += f"${len(arg_str)}\r\n{arg_str}\r\n".encode()
        
        self.socket.sendall(cmd_bytes)
        
        # Receive response
        response = self.socket.recv(4096).decode('utf-8', errors='ignore')
        return response
    
    def add_benchmark(self, name: str, operation: callable, iterations: int = 1000):
        """Add benchmark to suite"""
        self.benchmarks.append(Benchmark(name, operation, iterations))
    
    def run_all(self) -> List[Dict[str, Any]]:
        """Run all benchmarks"""
        self.results.clear()
        
        for benchmark in self.benchmarks:
            print(f"Running: {benchmark.name}...", end=" ", flush=True)
            result = benchmark.run()
            self.results.append(result)
            print(f"✓ ({result['throughput']:.0f} ops/sec)")
        
        return self.results
    
    def print_results(self):
        """Print formatted results"""
        print("\n" + "=" * 120)
        print(f"{'Benchmark':<30} {'Min(μs)':<12} {'Mean(μs)':<12} {'Max(μs)':<12} {'P95(μs)':<12} {'Throughput':<15}")
        print("=" * 120)
        
        for result in self.results:
            print(f"{result['name']:<30} "
                  f"{result['min']:<12.2f} "
                  f"{result['mean']:<12.2f} "
                  f"{result['max']:<12.2f} "
                  f"{result['p95']:<12.2f} "
                  f"{result['throughput']:<15.0f} ops/sec")
        
        print("=" * 120 + "\n")


class StressTester:
    """Stress test cache with concurrent load"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.results = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_time_sec": 0,
            "throughput": 0,
            "errors": []
        }
    
    def stress_test(self, num_threads: int = 10, requests_per_thread: int = 100,
                   duration_seconds: int = 30) -> Dict[str, Any]:
        """
        Run stress test with concurrent threads
        
        Args:
            num_threads: Number of concurrent threads
            requests_per_thread: Requests per thread
            duration_seconds: Duration limit
        """
        print(f"[STRESS] Starting with {num_threads} threads, {requests_per_thread} req/thread...")
        
        self.results = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_time_sec": 0,
            "throughput": 0,
            "errors": []
        }
        
        threads = []
        start_time = time.time()
        
        # Start threads
        for i in range(num_threads):
            thread = threading.Thread(
                target=self._worker_thread,
                args=(i, requests_per_thread, duration_seconds)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        self.results["total_time_sec"] = end_time - start_time
        
        if self.results["total_time_sec"] > 0:
            self.results["throughput"] = self.results["successful"] / self.results["total_time_sec"]
        
        return self.results
    
    def _worker_thread(self, thread_id: int, num_requests: int, duration_limit: int):
        """Worker thread for stress testing"""
        try:
            socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_obj.connect((self.host, self.port))
            
            start_time = time.time()
            request_count = 0
            
            while request_count < num_requests:
                if time.time() - start_time > duration_limit:
                    break
                
                try:
                    # Send SET command
                    key = f"stress:thread{thread_id}:req{request_count}"
                    value = f"value_{request_count}"
                    
                    cmd = f"*3\r\n$3\r\nSET\r\n${len(key)}\r\n{key}\r\n${len(value)}\r\n{value}\r\n".encode()
                    socket_obj.sendall(cmd)
                    response = socket_obj.recv(1024)
                    
                    self.results["successful"] += 1
                    
                except Exception as e:
                    self.results["failed"] += 1
                    self.results["errors"].append(str(e))
                
                self.results["total_requests"] += 1
                request_count += 1
            
            socket_obj.close()
        
        except Exception as e:
            print(f"[ERROR] Thread {thread_id}: {e}")
    
    def print_results(self):
        """Print stress test results"""
        print("\n" + "=" * 80)
        print("STRESS TEST RESULTS")
        print("=" * 80)
        print(f"Total Requests:    {self.results['total_requests']}")
        print(f"Successful:        {self.results['successful']}")
        print(f"Failed:            {self.results['failed']}")
        print(f"Duration (sec):    {self.results['total_time_sec']:.2f}")
        print(f"Throughput:        {self.results['throughput']:.0f} ops/sec")
        print(f"Success Rate:      {(self.results['successful'] / self.results['total_requests'] * 100):.1f}%")
        
        if self.results['errors']:
            print(f"\nSample Errors: {self.results['errors'][:3]}")
        
        print("=" * 80 + "\n")
