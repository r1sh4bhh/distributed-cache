import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

class CacheEntry:
    """Represents a cached value with metadata"""
    def __init__(self, value: Any, ttl: Optional[int] = None):
        self.value = value
        self.created_at = time.time()
        self.accessed_at = time.time()
        self.ttl = ttl  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        """Update access time for LRU tracking"""
        self.accessed_at = time.time()


class StorageEngine:
    """In-memory storage with LRU eviction"""
    
    def __init__(self, max_memory_mb: int = 100, eviction_policy: str = "lru", persistence=None):
        self.store: Dict[str, CacheEntry] = {}
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.eviction_policy = eviction_policy  # "lru", "fifo", "random"
        self.memory_used = 0
        self.persistence = persistence  # Optional PersistenceManager
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a key-value pair
        
        Args:
            key: Cache key
            value: Value to store (any Python object)
            ttl: Time to live in seconds (None = never expires)
        
        Returns:
            True if stored, False if memory exceeded after eviction
        """
        # Remove old entry if exists
        if key in self.store:
            self.memory_used -= self._estimate_size(self.store[key].value)
        
        # Create new entry
        entry = CacheEntry(value, ttl)
        value_size = self._estimate_size(value)
        
        # Check if we need to evict
        while self.memory_used + value_size > self.max_memory_bytes and self.store:
            self._evict_one()
        
        # Store entry
        self.store[key] = entry
        self.memory_used += value_size
        
        # Log to persistence (if enabled)
        if self.persistence:
            if ttl:
                self.persistence.log_command("SET", [key, value, ttl])
            else:
                self.persistence.log_command("SET", [key, value])
        
        return True
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value by key
        
        Returns:
            Value if found and not expired, None otherwise
        """
        if key not in self.store:
            return None
        
        entry = self.store[key]
        
        # Check expiration
        if entry.is_expired():
            self.memory_used -= self._estimate_size(entry.value)
            del self.store[key]
            return None
        
        # Update access time for LRU
        entry.access()
        return entry.value
    
    def delete(self, key: str) -> bool:
        """Delete a key"""
        if key not in self.store:
            return False
        
        entry = self.store[key]
        self.memory_used -= self._estimate_size(entry.value)
        del self.store[key]
        return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists (and is not expired)"""
        return self.get(key) is not None
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time on existing key"""
        if key not in self.store:
            return False
        
        self.store[key].ttl = seconds
        self.store[key].created_at = time.time()
        return True
    
    def ttl(self, key: str) -> int:
        """
        Get remaining TTL
        
        Returns:
            Remaining seconds, -1 if no expiration, -2 if not found
        """
        if key not in self.store:
            return -2
        
        entry = self.store[key]
        
        if entry.is_expired():
            self.delete(key)
            return -2
        
        if entry.ttl is None:
            return -1
        
        remaining = entry.ttl - (time.time() - entry.created_at)
        return max(0, int(remaining))
    
    def keys(self, pattern: str = "*") -> list:
        """Get all keys (simple pattern matching)"""
        # Remove expired keys first
        expired = [k for k, v in self.store.items() if v.is_expired()]
        for k in expired:
            self.delete(k)
        
        if pattern == "*":
            return list(self.store.keys())
        
        # Simple wildcard matching
        import fnmatch
        return [k for k in self.store.keys() if fnmatch.fnmatch(k, pattern)]
    
    def flush_all(self) -> int:
        """Clear all entries"""
        count = len(self.store)
        self.store.clear()
        self.memory_used = 0
        return count
    
    def info(self) -> Dict[str, Any]:
        """Get cache statistics"""
        # Remove expired entries
        expired = [k for k, v in self.store.items() if v.is_expired()]
        for k in expired:
            self.delete(k)
        
        return {
            "keys_count": len(self.store),
            "memory_used_bytes": self.memory_used,
            "memory_used_mb": self.memory_used / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "eviction_policy": self.eviction_policy
        }
    
    # Private methods
    
    def _evict_one(self):
        """Evict one entry based on policy"""
        if not self.store:
            return
        
        if self.eviction_policy == "lru":
            self._evict_lru()
        elif self.eviction_policy == "fifo":
            self._evict_fifo()
        elif self.eviction_policy == "random":
            self._evict_random()
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        lru_key = min(self.store.keys(), 
                     key=lambda k: self.store[k].accessed_at)
        entry = self.store[lru_key]
        self.memory_used -= self._estimate_size(entry.value)
        del self.store[lru_key]
    
    def _evict_fifo(self):
        """Evict first in (oldest created) entry"""
        fifo_key = min(self.store.keys(),
                      key=lambda k: self.store[k].created_at)
        entry = self.store[fifo_key]
        self.memory_used -= self._estimate_size(entry.value)
        del self.store[fifo_key]
    
    def _evict_random(self):
        """Evict random entry"""
        import random
        key = random.choice(list(self.store.keys()))
        entry = self.store[key]
        self.memory_used -= self._estimate_size(entry.value)
        del self.store[key]
    
    def _estimate_size(self, obj: Any) -> int:
        """Rough estimate of object size in bytes"""
        import sys
        return sys.getsizeof(obj)
