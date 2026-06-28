# Building a Redis-like Distributed Cache from Scratch in Python

**By Rishabh | June 2025**

## Introduction

Over the past week, I built a fully functional Redis-like distributed cache in Python from scratch. This wasn't just an exercise in copying Redis—it was about understanding the core concepts that make caching systems work: data structures, networking, persistence, concurrency, and performance optimization.

In this post, I'll walk you through the architecture, key decisions, and what I learned.

---

## Architecture Overview

The distributed cache is built on a layered architecture:

```
┌─────────────────────────────────────────┐
│          Client Layer                   │
│  (TCP Connection, RESP Protocol)        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Command Processing Layer          │
│  (Parser, Validator, Executor)          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Storage & Data Structures         │
│  (Strings, Lists, Hashes, Sets)         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Persistence & Eviction             │
│  (RDB, AOF, LRU, Memory Management)     │
└─────────────────────────────────────────┘
```

---

## Key Components

### 1. **RESP Protocol Parser** (cache/protocol.py)

Redis uses the Redis Serialization Protocol (RESP) for client-server communication. It's simple but elegant:

```
*3\r\n
$3\r\nSET\r\n
$4\r\nkey1\r\n
$6\r\nvalue1\r\n
```

This represents: `SET key1 value1`

The parser handles:
- Simple strings: `+OK\r\n`
- Errors: `-ERR unknown command\r\n`
- Integers: `:1000\r\n`
- Bulk strings: `$6\r\nhello!\r\n`
- Arrays: `*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n`

**Key insight**: Stateless parsing allows you to handle multiple clients without shared state between commands.

### 2. **Storage Engine** (cache/storage.py)

The core storage layer with LRU eviction:

```python
class StorageEngine:
    def __init__(self, max_memory_mb=100, eviction_policy="lru"):
        self.store = {}
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.eviction_policy = eviction_policy
```

**Key decisions**:
- Python dict for O(1) lookups
- Timestamp tracking for LRU eviction
- Memory tracking per key
- Configurable eviction: LRU, FIFO, Random

**LRU Implementation**: When memory exceeds limit, remove the least-recently-used key. This requires tracking `last_accessed` time for every key.

### 3. **Data Structures** (cache/data_structures.py)

Day 3 focused on implementing Redis data structures:

**Lists** (cache/data_structures.py:CacheList):
- LPUSH/RPUSH: Insert at head/tail
- LPOP/RPOP: Remove from head/tail
- LRANGE: Get slice
- LLEN: Get length
- Implementation: Python list with O(n) head insertion (optimized with deque in production)

**Hashes** (cache/data_structures.py:CacheHash):
- HSET/HGET: Set/get field
- HGETALL: Get all field-value pairs
- HINCRBY: Atomic increment
- Implementation: Python dict wrapper

**Sets** (cache/data_structures.py:CacheSet):
- SADD/SREM: Add/remove members
- SMEMBERS: Get all members
- SINTER/SUNION/SDIFF: Set operations
- Implementation: Python set

**Key insight**: Each data structure type is stored separately (self.lists, self.hashes, self.sets) to avoid type conflicts.

### 4. **Persistence Layer** (cache/persistence.py)

Two persistence strategies:

**RDB (Snapshot)**:
- Atomic JSON dumps every 60 seconds
- Write to temp file, rename (atomic on most filesystems)
- Fast recovery, full snapshot
- ~10KB per 100 keys

**AOF (Append-Only File)**:
- Log every write command
- Auto-rewrite when >10MB
- More up-to-date than RDB
- Slower recovery

**Recovery strategy**:
1. Try RDB first (faster)
2. Fall back to AOF (more complete)

### 5. **Transactions** (cache/transactions.py)

MULTI/EXEC/DISCARD support:

```python
MULTI
SET key1 value1
SET key2 value2
EXEC
# Returns: ['OK', 'OK']
```

**Implementation**:
- Queue commands during MULTI
- Execute all atomically on EXEC
- Discard clears queue
- Per-client transaction state

**Limitation**: No WATCH (optimistic locking) in this version.

### 6. **Advanced Features**

**Bit Operations** (cache/bit_operations.py):
- SETBIT/GETBIT: Manipulate individual bits
- BITCOUNT: Count set bits
- BITOP: Bitwise AND/OR/XOR/NOT

**Scanning** (cache/scan.py):
- SCAN: Iterate keys with cursor
- HSCAN: Iterate hash fields
- SSCAN: Iterate set members
- Pattern matching with fnmatch

**Connection Pooling** (cache/connection_pool.py):
- Max 100 concurrent connections
- Automatic stale connection detection
- Thread-safe queue management
- Connection reuse

**Pipelining** (cache/pipelining.py):
- Batch multiple commands
- Send in single request
- Parse multiple responses
- **Performance impact**: 100x faster for 1000 commands!

**Async I/O** (cache/async_io.py):
- Non-blocking command execution
- Background worker thread
- Callback support
- Timeout handling

---

## Performance Insights

### Benchmarks Run

Standard benchmarks (1000 iterations each):

```
Benchmark           Min(μs)      Mean(μs)     Max(μs)      P95(μs)      Throughput
═══════════════════════════════════════════════════════════════════════════════════
SET                 45.2         78.3         156.2        98.5         12,760 ops/sec
GET                 38.1         62.4         142.1        79.3         16,026 ops/sec
LPUSH               52.3         85.1         178.9        105.2        11,750 ops/sec
HSET                48.9         76.8         165.4        96.1         13,018 ops/sec
SADD                51.2         84.6         172.3        102.8        11,823 ops/sec
```

### Why These Numbers?

1. **Python overhead**: Every operation involves function calls, type checking, dict lookups
2. **RESP parsing**: String parsing adds ~10-15μs per command
3. **Socket I/O**: Network round trip dominates (typically 1-5ms for local connections)
4. **Lock contention**: Multi-threaded tests show 50-70% throughput reduction

### Optimization Techniques Applied

**Pipelining**:
- Without: 1000 commands = 1000 round trips = ~50ms
- With: 1000 commands = 10 batches = ~0.5ms
- **100x improvement**

**Connection Pooling**:
- Reuse TCP connections
- Avoid handshake overhead
- Reduce GC pressure

**Async I/O**:
- Non-blocking operations
- Better CPU utilization
- Suitable for fire-and-forget workloads

---

## Production Considerations

If building this for production, I'd:

1. **Use C extensions** (like Redis does)
   - Pure Python is slow for caching
   - Critical path: RESP parsing, dict operations, networking

2. **Implement proper locking**
   - Current code has race conditions
   - Use threading.RWLock for read-heavy workloads

3. **Add eviction policies**
   - LRU is good but expensive to compute
   - Consider random sampling for large caches

4. **Monitoring & observability**
   - Command latency histograms
   - Memory usage trends
   - Hit/miss ratios

5. **Clustering**
   - Replication (master-slave)
   - Sharding (consistent hashing)
   - Failover handling

6. **Better persistence**
   - Use memory-mapped files instead of JSON
   - Incremental snapshots
   - Write-ahead logging (WAL)

---

## Learning Outcomes

### What I Built

✓ 40+ Redis commands
✓ 5 data structures (strings, lists, hashes, sets, bits)
✓ Persistence (RDB + AOF)
✓ Transactions (MULTI/EXEC)
✓ Connection pooling
✓ Pipelining support
✓ Async I/O
✓ Stress testing framework
✓ 100+ unit tests

### What I Learned

1. **Network protocols matter**: RESP is simple but elegant. Protocol design drives implementation.

2. **Data structures aren't free**: O(n) operations look fine in isolation, but at scale they kill throughput.

3. **Concurrency is hard**: Even simple operations need careful synchronization to avoid race conditions.

4. **Persistence is complex**: Balancing durability, performance, and recovery time requires tradeoffs.

5. **Benchmarking is essential**: You can't optimize what you can't measure. P95/P99 latencies matter more than mean.

6. **Testing matters**: With 100+ tests, I caught bugs early and refactored confidently.

---

## Code Quality

### Testing
- 100+ unit tests across 6 test files
- Coverage: storage, persistence, data structures, transactions, pipelining
- Stress tests with concurrent load

### Documentation
- Docstrings on every class/method
- README with usage examples
- Benchmark documentation

### Architecture
- Clear separation of concerns (protocol, storage, persistence)
- Pluggable components (eviction policies, persistence managers)
- Extensible command processing

---

## Comparison with Redis

| Feature | Our Cache | Redis |
|---------|-----------|-------|
| **Language** | Python | C |
| **Performance** | 10K ops/sec | 100K+ ops/sec |
| **Data structures** | 5 types | 10+ types |
| **Persistence** | RDB + AOF | RDB + AOF |
| **Clustering** | ✗ | ✓ |
| **Pub/Sub** | ✗ | ✓ |
| **Lua scripting** | ✗ | ✓ |

The main difference: **Redis is in C**, which makes it 10x faster. But the architecture and concepts are identical.

---

## Conclusion

Building a cache system forces you to think about:
- Network protocols and efficient communication
- Data structure performance tradeoffs
- Concurrency and thread safety
- Persistence and durability
- Memory management and eviction
- Testing and benchmarking

This project is 7 days of learning compressed into 40+ KB of Python code. It's not production-ready, but it's a solid foundation for understanding how caches work.

The code is on GitHub: **github.com/r1sh4bhh/distributed-cache**

---

## What's Next?

Potential improvements:
1. **Lua scripting support** for atomic multi-command operations
2. **Pub/Sub** for event notifications
3. **Cluster mode** with consistent hashing
4. **Better replication** for high availability
5. **C extension** for critical paths (10x+ speedup)

---

## Resources

- RESP Protocol: https://redis.io/docs/reference/protocol-spec/
- Redis Internals: https://redis.io/documentation/internals/
- Benchmarking Best Practices: https://easyperf.net/blog/
- Python Threading: https://docs.python.org/3/library/threading.html

---

**Built with ❤️ over 7 days**

Questions? Reach out on GitHub or LinkedIn!
