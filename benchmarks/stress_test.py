"""
Stress testing for distributed cache
Tests system under high load
"""

import time
import threading
import random
import string
from typing import Dict, List
from cache.client import CacheClient


class StressTestResult:
    """Results from stress test"""
    
    def __init__(self, name: str):
        self.name = name
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.total_time = 0
        self.min_latency = float('inf')
        self.max_latency = 0
        self.avg_latency = 0
        self.throughput = 0
    
    def calculate(self):
        """Calculate final metrics"""
        if self.total_time > 0:
            self.throughput = self.successful_operations / self.total_time
        
        if self.successful_operations > 0:
            self.avg_latency = self.avg_latency / self.successful_operations
    
    def print_results(self):
        """Print results"""
        print(f"\n{self.name}:")
        print(f"  Total Operations: {self.total_operations}")
        print(f"  Successful: {self.successful_operations}")
        print(f"  Failed: {self.failed_operations}")
        print(f"  Success Rate: {100 * self.successful_operations / self.total_operations:.1f}%")
        print(f"  Total Time: {self.total_time:.2f}s")
        print(f"  Throughput: {self.throughput:.0f} ops/sec")
        print(f"  Min Latency: {self.min_latency:.3f}ms")
        print(f"  Max Latency: {self.max_latency:.3f}ms")
        print(f"  Avg Latency: {self.avg_latency:.3f}ms")


class DistributedCacheStressTester:
    """Stress testing suite"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
    
    def stress_test_high_throughput(self, num_threads: int = 20, duration_seconds: int = 30) -> StressTestResult:
        """High throughput stress test"""
        print(f"\n[STRESS] High Throughput ({num_threads} threads, {duration_seconds}s)")
        
        result = StressTestResult("High Throughput Test")
        lock = threading.Lock()
        stop_event = threading.Event()
        
        def worker():
            client = CacheClient(self.host, self.port)
            try:
                if not client.connect():
                    return
                
                while not stop_event.is_set():
                    key = f"stress_key_{random.randint(0, 10000)}"
                    value = f"value_{random.randint(0, 100000)}"
                    
                    start = time.time()
                    try:
                        if random.random() < 0.5:
                            client.set(key, value)
                        else:
                            client.get(key)
                        
                        latency = (time.time() - start) * 1000
                        
                        with lock:
                            result.successful_operations += 1
                            result.min_latency = min(result.min_latency, latency)
                            result.max_latency = max(result.max_latency, latency)
                            result.avg_latency += latency
                            result.total_operations += 1
                    
                    except Exception as e:
                        with lock:
                            result.failed_operations += 1
                            result.total_operations += 1
            
            finally:
                client.disconnect()
        
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            t = threading.Thread(target=worker, daemon=True)
            threads.append(t)
            t.start()
        
        time.sleep(duration_seconds)
        stop_event.set()
        
        for t in threads:
            t.join(timeout=5)
        
        result.total_time = time.time() - start_time
        result.calculate()
        result.print_results()
        
        return result
    
    def stress_test_large_values(self, num_threads: int = 10, value_size_kb: int = 100) -> StressTestResult:
        """Test with large values"""
        print(f"\n[STRESS] Large Values ({num_threads} threads, {value_size_kb}KB each)")
        
        result = StressTestResult("Large Values Test")
        lock = threading.Lock()
        large_value = "x" * (value_size_kb * 1024)
        
        def worker(thread_id: int):
            client = CacheClient(self.host, self.port)
            try:
                if not client.connect():
                    return
                
                for i in range(100):
                    key = f"large_value_{thread_id}_{i}"
                    
                    start = time.time()
                    try:
                        client.set(key, large_value)
                        latency = (time.time() - start) * 1000
                        
                        with lock:
                            result.successful_operations += 1
                            result.min_latency = min(result.min_latency, latency)
                            result.max_latency = max(result.max_latency, latency)
                            result.avg_latency += latency
                            result.total_operations += 1
                    
                    except Exception:
                        with lock:
                            result.failed_operations += 1
                            result.total_operations += 1
            
            finally:
                client.disconnect()
        
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,), daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=30)
        
        result.total_time = time.time() - start_time
        result.calculate()
        result.print_results()
        
        return result
    
    def stress_test_memory_pressure(self, num_threads: int = 10, keys_per_thread: int = 1000) -> StressTestResult:
        """Test memory usage under pressure"""
        print(f"\n[STRESS] Memory Pressure ({num_threads} threads, {keys_per_thread} keys each)")
        
        result = StressTestResult("Memory Pressure Test")
        lock = threading.Lock()
        
        def worker(thread_id: int):
            client = CacheClient(self.host, self.port)
            try:
                if not client.connect():
                    return
                
                for i in range(keys_per_thread):
                    key = f"mem_key_{thread_id}_{i}"
                    value = "x" * random.randint(1000, 10000)
                    
                    start = time.time()
                    try:
                        client.set(key, value)
                        latency = (time.time() - start) * 1000
                        
                        with lock:
                            result.successful_operations += 1
                            result.min_latency = min(result.min_latency, latency)
                            result.max_latency = max(result.max_latency, latency)
                            result.avg_latency += latency
                            result.total_operations += 1
                    
                    except Exception:
                        with lock:
                            result.failed_operations += 1
                            result.total_operations += 1
            
            finally:
                client.disconnect()
        
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,), daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        result.total_time = time.time() - start_time
        result.calculate()
        result.print_results()
        
        return result
    
    def stress_test_rapid_reconnects(self, num_threads: int = 20, iterations: int = 100) -> StressTestResult:
        """Test rapid connects/disconnects"""
        print(f"\n[STRESS] Rapid Reconnects ({num_threads} threads, {iterations} iterations)")
        
        result = StressTestResult("Rapid Reconnects Test")
        lock = threading.Lock()
        
        def worker():
            for _ in range(iterations):
                client = CacheClient(self.host, self.port)
                
                start = time.time()
                try:
                    if client.connect():
                        client.set("reconnect_test", f"value_{time.time()}")
                        client.get("reconnect_test")
                        client.disconnect()
                        
                        latency = (time.time() - start) * 1000
                        
                        with lock:
                            result.successful_operations += 1
                            result.min_latency = min(result.min_latency, latency)
                            result.max_latency = max(result.max_latency, latency)
                            result.avg_latency += latency
                            result.total_operations += 1
                    else:
                        with lock:
                            result.failed_operations += 1
                            result.total_operations += 1
                
                except Exception:
                    with lock:
                        result.failed_operations += 1
                        result.total_operations += 1
        
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            t = threading.Thread(target=worker, daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        result.total_time = time.time() - start_time
        result.calculate()
        result.print_results()
        
        return result
    
    def stress_test_mixed_operations(self, num_threads: int = 15, duration_seconds: int = 60) -> StressTestResult:
        """Test mixed operations (SET, GET, DEL, LPUSH, HSET, SADD)"""
        print(f"\n[STRESS] Mixed Operations ({num_threads} threads, {duration_seconds}s)")
        
        result = StressTestResult("Mixed Operations Test")
        lock = threading.Lock()
        stop_event = threading.Event()
        
        def worker():
            client = CacheClient(self.host, self.port)
            try:
                if not client.connect():
                    return
                
                while not stop_event.is_set():
                    operation = random.choice([
                        lambda: client.set(f"key_{random.randint(0, 1000)}", f"val_{random.randint(0, 1000)}"),
                        lambda: client.get(f"key_{random.randint(0, 1000)}"),
                        lambda: client._send_command("LPUSH", "list", f"val_{random.randint(0, 1000)}"),
                        lambda: client._send_command("HSET", "hash", f"f_{random.randint(0, 100)}", f"v_{random.randint(0, 1000)}"),
                        lambda: client._send_command("SADD", "set", f"member_{random.randint(0, 1000)}"),
                    ])
                    
                    start = time.time()
                    try:
                        operation()
                        latency = (time.time() - start) * 1000
                        
                        with lock:
                            result.successful_operations += 1
                            result.min_latency = min(result.min_latency, latency)
                            result.max_latency = max(result.max_latency, latency)
                            result.avg_latency += latency
                            result.total_operations += 1
                    
                    except Exception:
                        with lock:
                            result.failed_operations += 1
                            result.total_operations += 1
            
            finally:
                client.disconnect()
        
        threads = []
        start_time = time.time()
        
        for _ in range(num_threads):
            t = threading.Thread(target=worker, daemon=True)
            threads.append(t)
            t.start()
        
        time.sleep(duration_seconds)
        stop_event.set()
        
        for t in threads:
            t.join(timeout=10)
        
        result.total_time = time.time() - start_time
        result.calculate()
        result.print_results()
        
        return result


def main():
    """Run all stress tests"""
    tester = DistributedCacheStressTester()
    
    print("="*80)
    print("DISTRIBUTED CACHE STRESS TESTS")
    print("="*80)
    print("[INFO] Make sure server is running on localhost:6379")
    
    try:
        # Run stress tests
        tester.stress_test_high_throughput(num_threads=10, duration_seconds=20)
        tester.stress_test_large_values(num_threads=5, value_size_kb=100)
        tester.stress_test_memory_pressure(num_threads=10, keys_per_thread=500)
        tester.stress_test_rapid_reconnects(num_threads=10, iterations=50)
        tester.stress_test_mixed_operations(num_threads=10, duration_seconds=30)
        
        print("\n" + "="*80)
        print("ALL STRESS TESTS COMPLETED")
        print("="*80)
    
    except KeyboardInterrupt:
        print("\n[INFO] Tests interrupted by user")


if __name__ == "__main__":
    main()
