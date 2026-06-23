import time
import statistics
from cache.client import CacheClient


class CacheBenchmark:
    """Benchmark cache performance"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.client = CacheClient(host, port)
        self.results = {}
    
    def connect(self) -> bool:
        """Connect to cache server"""
        return self.client.connect()
    
    def disconnect(self):
        """Disconnect from server"""
        self.client.disconnect()
    
    def benchmark_set(self, num_operations: int = 10000) -> dict:
        """Benchmark SET operations"""
        print(f"\n[BENCHMARK] SET ({num_operations} ops)")
        
        times = []
        for i in range(num_operations):
            key = f"key:{i}"
            value = f"value_{i}"
            
            start = time.time()
            self.client.set(key, value)
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)
        
        return self._calculate_stats(times, "SET")
    
    def benchmark_get(self, num_operations: int = 10000) -> dict:
        """Benchmark GET operations"""
        print(f"[BENCHMARK] GET ({num_operations} ops)")
        
        # Pre-populate keys
        for i in range(num_operations):
            self.client.set(f"key:{i}", f"value_{i}")
        
        times = []
        for i in range(num_operations):
            key = f"key:{i}"
            
            start = time.time()
            self.client.get(key)
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)
        
        return self._calculate_stats(times, "GET")
    
    def benchmark_mixed(self, num_operations: int = 10000) -> dict:
        """Benchmark mixed SET/GET operations"""
        print(f"[BENCHMARK] Mixed 50% SET + 50% GET ({num_operations} ops)")
        
        times = []
        for i in range(num_operations):
            key = f"key:{i}"
            value = f"value_{i}"
            
            if i % 2 == 0:
                # SET operation
                start = time.time()
                self.client.set(key, value)
                elapsed = (time.time() - start) * 1000
            else:
                # GET operation
                start = time.time()
                self.client.get(key)
                elapsed = (time.time() - start) * 1000
            
            times.append(elapsed)
        
        return self._calculate_stats(times, "Mixed")
    
    def benchmark_with_expiration(self, num_operations: int = 1000) -> dict:
        """Benchmark SET with expiration"""
        print(f"[BENCHMARK] SET with EX ({num_operations} ops)")
        
        times = []
        for i in range(num_operations):
            key = f"expiring:{i}"
            value = f"value_{i}"
            
            start = time.time()
            self.client.set(key, value, ex=3600)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        return self._calculate_stats(times, "SET with EX")
    
    def benchmark_delete(self, num_operations: int = 1000) -> dict:
        """Benchmark DELETE operations"""
        print(f"[BENCHMARK] DEL ({num_operations} ops)")
        
        # Pre-populate keys
        for i in range(num_operations):
            self.client.set(f"del_key:{i}", f"value_{i}")
        
        times = []
        for i in range(num_operations):
            key = f"del_key:{i}"
            
            start = time.time()
            self.client.delete(key)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        return self._calculate_stats(times, "DEL")
    
    def benchmark_throughput(self, duration_seconds: int = 5) -> dict:
        """Benchmark operations per second"""
        print(f"[BENCHMARK] Throughput test ({duration_seconds}s)")
        
        start = time.time()
        count = 0
        
        while time.time() - start < duration_seconds:
            self.client.set(f"throughput:{count}", f"value_{count}")
            count += 1
        
        elapsed = time.time() - start
        ops_per_second = count / elapsed
        
        return {
            "operation": "Throughput",
            "ops_per_second": ops_per_second,
            "total_ops": count,
            "duration_seconds": elapsed
        }
    
    def _calculate_stats(self, times: list, operation: str) -> dict:
        """Calculate statistics from timing data"""
        return {
            "operation": operation,
            "count": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)],
            "p99_ms": sorted(times)[int(len(times) * 0.99)]
        }
    
    def print_results(self):
        """Print benchmark results"""
        print("\n" + "="*70)
        print("CACHE BENCHMARK RESULTS")
        print("="*70)
        
        for op_name, stats in self.results.items():
            print(f"\n{op_name}:")
            print(f"  Count: {stats.get('count', stats.get('total_ops', 'N/A'))}")
            
            if "ops_per_second" in stats:
                print(f"  Throughput: {stats['ops_per_second']:.0f} ops/sec")
            else:
                print(f"  Min: {stats.get('min_ms', 'N/A'):.3f}ms")
                print(f"  Max: {stats.get('max_ms', 'N/A'):.3f}ms")
                print(f"  Avg: {stats.get('avg_ms', 'N/A'):.3f}ms")
                print(f"  Median: {stats.get('median_ms', 'N/A'):.3f}ms")
                print(f"  P95: {stats.get('p95_ms', 'N/A'):.3f}ms")
                print(f"  P99: {stats.get('p99_ms', 'N/A'):.3f}ms")
        
        print("\n" + "="*70)


def main():
    """Run benchmarks"""
    benchmark = CacheBenchmark()
    
    if not benchmark.connect():
        print("[ERROR] Could not connect to cache server")
        return
    
    print("[BENCHMARK] Starting cache benchmarks...")
    
    # Run benchmarks
    benchmark.results["SET"] = benchmark.benchmark_set(10000)
    benchmark.results["GET"] = benchmark.benchmark_get(10000)
    benchmark.results["Mixed"] = benchmark.benchmark_mixed(10000)
    benchmark.results["SET with EX"] = benchmark.benchmark_with_expiration(1000)
    # Skip DEL and Throughput - causes connection issues on Windows
    # benchmark.results["DEL"] = benchmark.benchmark_delete(1000)
    # benchmark.results["Throughput"] = benchmark.benchmark_throughput(5)
    
    # Print results
    benchmark.print_results()
    
    benchmark.disconnect()


if __name__ == "__main__":
    main()
