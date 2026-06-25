# Benchmarking & Performance Testing

## Overview

This directory contains comprehensive benchmarking tools for the distributed cache project.

## Components

### 1. **advanced_benchmark.py**
Core benchmarking infrastructure:
- `Benchmark`: Single benchmark test with statistical analysis
- `BenchmarkSuite`: Collection of benchmarks with RESP protocol support
- `StressTester`: Concurrent load testing with multiple threads
- `ComparisonBenchmark`: Compare performance against Redis (future)

### 2. **run_benchmarks.py**
Executable benchmark runner with predefined test scenarios:
- Standard benchmarks (SET, GET, LPUSH, HSET, SADD, SETBIT)
- Light stress test (5 threads, 100 req/thread)
- Medium stress test (10 threads, 100 req/thread)
- Heavy stress test (20 threads, 50 req/thread)
- Sustained load test (5000 operations)

## Usage

### Run All Benchmarks

```bash
# Terminal 1: Start cache server
python -m cache.server

# Terminal 2: Run benchmarks
python benchmarks/run_benchmarks.py
```

### Run Individual Benchmarks

```python
from benchmarks.advanced_benchmark import BenchmarkSuite

suite = BenchmarkSuite("localhost", 6379)
suite.connect()

# Add benchmarks
suite.add_benchmark("SET", lambda: suite._send_command("SET", "key", "value"), 1000)
suite.add_benchmark("GET", lambda: suite._send_command("GET", "key"), 1000)

# Run and print results
suite.run_all()
suite.print_results()
suite.disconnect()
```

### Run Stress Test

```python
from benchmarks.advanced_benchmark import StressTester

tester = StressTester("localhost", 6379)
results = tester.stress_test(num_threads=10, requests_per_thread=100, duration_seconds=30)
tester.print_results()
```

## Metrics Explained

### Latency Metrics (μs - microseconds)
- **Min**: Fastest operation time
- **Mean**: Average operation time
- **Max**: Slowest operation time
- **P95**: 95th percentile (95% of ops are faster than this)
- **P99**: 99th percentile (99% of ops are faster than this)

### Throughput
- **Throughput**: Operations per second (higher is better)
- **Total Time**: Total time to execute all iterations

### Stress Test Results
- **Total Requests**: Total operations attempted
- **Successful**: Completed without error
- **Failed**: Operations that errored
- **Success Rate**: Percentage of successful operations
- **Throughput**: Operations per second under concurrent load

## Expected Results

### Standard Benchmarks
- SET/GET: 5,000 - 15,000 ops/sec
- LPUSH/LPOP: 4,000 - 12,000 ops/sec
- HSET/HGET: 4,000 - 12,000 ops/sec
- SADD/SMEMBERS: 3,000 - 10,000 ops/sec

### Stress Test
- Light Load: 1,000 - 5,000 ops/sec
- Medium Load: 2,000 - 8,000 ops/sec
- Heavy Load: 2,000 - 10,000 ops/sec

*Note: Actual results depend on CPU, memory, and network*

## Comparison with Redis

To compare against Redis:

```bash
# Install Redis
# brew install redis (macOS)
# apt-get install redis-server (Linux)

# Terminal 1: Start Redis
redis-server --port 6380

# Terminal 2: Run comparison
python -c "
from benchmarks.advanced_benchmark import ComparisonBenchmark
ComparisonBenchmark.compare(
    'Distributed Cache', 'localhost', 6379,
    'Redis', 'localhost', 6380,
    iterations=1000
)
"
```

## Files

```
benchmarks/
├── advanced_benchmark.py    # Core benchmark classes
├── run_benchmarks.py        # Executable benchmark runner
├── README.md                # This file
└── benchmark_results.txt    # Sample results (generated)
```

## Notes

- Run benchmarks on the same machine as the cache server
- Close other programs to reduce system noise
- Run multiple times to get consistent results
- P95/P99 latencies are more important than min/max for production workloads
