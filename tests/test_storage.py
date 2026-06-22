import unittest
import time
from cache.storage import StorageEngine, CacheEntry


class TestStorageEngine(unittest.TestCase):
    """Test StorageEngine"""
    
    def setUp(self):
        """Create fresh engine for each test"""
        self.engine = StorageEngine(max_memory_mb=10)
    
    def test_set_get(self):
        """Test basic SET/GET"""
        self.engine.set("key1", "value1")
        self.assertEqual(self.engine.get("key1"), "value1")
    
    def test_set_overwrite(self):
        """Test overwriting existing key"""
        self.engine.set("key1", "value1")
        self.engine.set("key1", "value2")
        self.assertEqual(self.engine.get("key1"), "value2")
    
    def test_get_nonexistent(self):
        """Test getting non-existent key"""
        self.assertIsNone(self.engine.get("nonexistent"))
    
    def test_delete(self):
        """Test DELETE"""
        self.engine.set("key1", "value1")
        self.assertTrue(self.engine.delete("key1"))
        self.assertIsNone(self.engine.get("key1"))
    
    def test_delete_nonexistent(self):
        """Test deleting non-existent key"""
        self.assertFalse(self.engine.delete("nonexistent"))
    
    def test_exists(self):
        """Test EXISTS"""
        self.engine.set("key1", "value1")
        self.assertTrue(self.engine.exists("key1"))
        self.assertFalse(self.engine.exists("nonexistent"))
    
    def test_ttl_no_expiration(self):
        """Test TTL with no expiration"""
        self.engine.set("key1", "value1")
        self.assertEqual(self.engine.ttl("key1"), -1)
    
    def test_ttl_with_expiration(self):
        """Test TTL with expiration"""
        self.engine.set("key1", "value1", ttl=10)
        ttl = self.engine.ttl("key1")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)
    
    def test_ttl_nonexistent(self):
        """Test TTL on non-existent key"""
        self.assertEqual(self.engine.ttl("nonexistent"), -2)
    
    def test_expiration(self):
        """Test key expiration"""
        self.engine.set("key1", "value1", ttl=1)
        self.assertEqual(self.engine.get("key1"), "value1")
        
        # Wait for expiration
        time.sleep(1.1)
        self.assertIsNone(self.engine.get("key1"))
    
    def test_expire(self):
        """Test EXPIRE command"""
        self.engine.set("key1", "value1")
        self.assertTrue(self.engine.expire("key1", 10))
        self.assertGreater(self.engine.ttl("key1"), 0)
    
    def test_keys_wildcard(self):
        """Test KEYS with wildcard"""
        self.engine.set("user:1", "alice")
        self.engine.set("user:2", "bob")
        self.engine.set("post:1", "hello")
        
        keys = self.engine.keys("user:*")
        self.assertEqual(len(keys), 2)
        self.assertIn("user:1", keys)
        self.assertIn("user:2", keys)
    
    def test_keys_all(self):
        """Test KEYS with * pattern"""
        self.engine.set("key1", "val1")
        self.engine.set("key2", "val2")
        
        keys = self.engine.keys()
        self.assertEqual(len(keys), 2)
    
    def test_flush_all(self):
        """Test FLUSHALL"""
        self.engine.set("key1", "val1")
        self.engine.set("key2", "val2")
        
        count = self.engine.flush_all()
        self.assertEqual(count, 2)
        self.assertEqual(len(self.engine.keys()), 0)
    
    def test_info(self):
        """Test INFO"""
        self.engine.set("key1", "value1")
        info = self.engine.info()
        
        self.assertIn("keys_count", info)
        self.assertIn("memory_used_bytes", info)
        self.assertEqual(info["keys_count"], 1)
    
    def test_lru_eviction(self):
        """Test LRU eviction when memory full"""
        small_engine = StorageEngine(max_memory_mb=1, eviction_policy="lru")
        
        # Fill with small values
        for i in range(100):
            small_engine.set(f"key{i}", "x" * 100)
        
        # Some early keys should have been evicted
        self.assertIsNone(small_engine.get("key0"))
    
    def test_fifo_eviction(self):
        """Test FIFO eviction when memory full"""
        small_engine = StorageEngine(max_memory_mb=1, eviction_policy="fifo")
        
        # Fill with small values
        for i in range(100):
            small_engine.set(f"key{i}", "x" * 100)
        
        # First key should be evicted
        self.assertIsNone(small_engine.get("key0"))


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry"""
    
    def test_not_expired(self):
        """Test entry without expiration"""
        entry = CacheEntry("value")
        self.assertFalse(entry.is_expired())
    
    def test_expired(self):
        """Test entry with expiration"""
        entry = CacheEntry("value", ttl=1)
        self.assertFalse(entry.is_expired())
        
        time.sleep(1.1)
        self.assertTrue(entry.is_expired())
    
    def test_access_update(self):
        """Test access time update"""
        entry = CacheEntry("value")
        old_time = entry.accessed_at
        
        time.sleep(0.1)
        entry.access()
        
        self.assertGreater(entry.accessed_at, old_time)


if __name__ == "__main__":
    unittest.main()
