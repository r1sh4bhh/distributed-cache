#!/usr/bin/env python3
"""
Benchmark runner for distributed cache
Run all benchmarks and generate report
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmarks.advanced_benchmark import BenchmarkSuite, StressTester
import time


def run_standard_benchmarks():
    """Run standard benchmarks"""
    print("\n" + "="*80)
    print("STANDARD BENCHMARKS - Distributed Cache")
    print("="*80)
    
    suite = BenchmarkSuite("localhost", 6379)
    
    if not suite.connect():
        print("[ERROR] Cannot connect to cache server on port 6379")
        return
    
    # String operations
    suite.add_benchmark(
        "SET (String)",
        lambda: suite._send_command("SET", "bench:key", "bench:value"),
        1000
    )
    
    suite.add_benchmark(
        "GET (String)",
        lambda: suite._send_command("GET", "bench:key"),
        1000
    )
    
    # List operations
    suite.add_benchmark(
        "LPUSH (List)",
        lambda: suite._send_command("LPUSH", "bench:list", "value"),
        1000
    )
    
    suite.add_benchmark(
        "LPOP (List)",
        lambda: suite._send_command("LPOP", "bench:list"),
        1000
    )
    
    # Hash operations
    suite.add_benchmark(
        "HSET (Hash)",
        lambda: suite._send_command("HSET", "bench:hash", "field", "value"),
        1000
    )
    
    suite.add_benchmark(
        "HGET (Hash)",
        lambda: suite._send_command("HGET", "bench:hash", "field"),
        1000
    )
    
    # Set operations
    suite.add_benchmark(
        "SADD (Set)",
        lambda: suite._send_command("SADD", "bench:set", "member"),
        1000
    )
    
    suite.add_benchmark(
        "SMEMBERS (Set)",
        lambda: suite._send_command("SMEMBERS", "bench:set"),
        1000
    )
    
    # Bit operations
    suite.add_benchmark(
        "SETBIT (Bit)",
        lambda: suite._send_command("SETBIT", "bench:bits", "0", "1"),
        1000
    )
    
    suite.add_benchmark(
        "GETBIT (Bit)",
        lambda: suite._send_command("GETBIT", "bench:bits", "0"),
        1000
    )
    
    # Run all
    suite.run_all()
    suite.print_results()
    suite.disconnect()


def run_stress_test():
    """Run stress test"""
    print("\n" + "="*80)
    print("STRESS TEST - Distributed Cache")
    print("="*80)
    
    tester = StressTester("localhost", 6379)
    
    # Small stress test: 5 threads, 100 requests each, 10 second limit
    print("\n[STRESS] Light Load (5 threads, 100 req/thread, 10s limit):")
    tester.stress_test(num_threads=5, requests_per_thread=100, duration_seconds=10)
    tester.print_results()
    
    # Medium stress test
    print("\n[STRESS] Medium Load (10 threads, 100 req/thread, 10s limit):")
    tester.stress_test(num_threads=10, requests_per_thread=100, duration_seconds=10)
    tester.print_results()
    
    # Heavy stress test
    print("\n[STRESS] Heavy Load (20 threads, 50 req/thread, 10s limit):")
    tester.stress_test(num_threads=20, requests_per_thread=50, duration_seconds=10)
    tester.print_results()


def run_sustained_test():
    """Run sustained load test"""
    print("\n" + "="*80)
    print("SUSTAINED LOAD TEST")
    print("="*80)
    
    suite = BenchmarkSuite("localhost", 6379)
    
    if not suite.connect():
        print("[ERROR] Cannot connect to cache server")
        return
    
    print("\nRunning 5000 SET operations...")
    suite.add_benchmark("SET (5000x)", lambda: suite._send_command("SET", "key", "value"), 5000)
    suite.run_all()
    suite.print_results()
    
    suite.disconnect()


def print_summary():
    """Print benchmark summary"""
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    print("""
Key Metrics Measured:
- Min/Max: Minimum and maximum operation time
- Mean: Average operation time
- P95/P99: 95th and 99th percentile latencies
- Throughput: Operations per second

Performance Notes:
- Single connection benchmarks measure basic throughput
- Stress tests measure concurrent load handling
- Sustained tests measure endurance and stability
""")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\n[BENCHMARK] Starting distributed cache benchmarks...\n")
    
    try:
        run_standard_benchmarks()
        run_stress_test()
        run_sustained_test()
        print_summary()
        
        print("[BENCHMARK] ✓ All benchmarks completed successfully!")
    
    except KeyboardInterrupt:
        print("\n[BENCHMARK] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
