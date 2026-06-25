import unittest
import time
from cache.storage import StorageEngine, CacheEntry


class TestStorageEngine(unittest.TestCase):
    """Test StorageEngine"""
    
    def setUp(self):
        self.engine = StorageEngine()
    
    def test_set_get(self):
        """Test basic set and get"""
        self.engine.set("key1", "value1")
        self.assertEqual(self.engine.get("key1"), "value1")
    
    def test_set_overwrite(self):
        """Test overwriting a key"""
        self.engine.set("key1", "value1")
        self.engine.set("key1", "value2")
        self.assertEqual(self.engine.get("key1"), "value2")
    
    def test_delete(self):
        """Test deleting a key"""
        self.engine.set("key1", "value1")
        self.assertTrue(self.engine.delete("key1"))
        self.assertIsNone(self.engine.get("key1"))
    
    def test_delete_nonexistent(self):
        """Test deleting non-existent key"""
        self.assertFalse(self.engine.delete("nonexistent"))
    
    def test_exists(self):
        """Test key existence"""
        self.engine.set("key1", "value1")
        self.assertTrue(self.engine.exists("key1"))
        self.assertFalse(self.engine.exists("nonexistent"))
    
    def test_get_nonexistent(self):
        """Test getting non-existent key"""
        self.assertIsNone(self.engine.get("nonexistent"))
    
    def test_expire(self):
        """Test setting expiration"""
        self.engine.set("key1", "value1", ttl=1)
        self.assertEqual(self.engine.get("key1"), "value1")
        time.sleep(1.1)
        self.assertIsNone(self.engine.get("key1"))
    
    def test_ttl(self):
        """Test TTL calculation"""
        self.engine.set("key1", "value1", ttl=10)
        ttl = self.engine.ttl("key1")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)
    
    def test_ttl_no_expiration(self):
        """Test TTL for non-expiring key"""
        self.engine.set("key1", "value1")
        self.assertEqual(self.engine.ttl("key1"), -1)
    
    def test_ttl_nonexistent(self):
        """Test TTL for non-existent key"""
        self.assertEqual(self.engine.ttl("nonexistent"), -2)
    
    def test_expiration(self):
        """Test expiration on access"""
        self.engine.set("key1", "value1", ttl=1)
        time.sleep(1.1)
        self.assertFalse(self.engine.exists("key1"))
    
    def test_keys_all(self):
        """Test getting all keys"""
        self.engine.set("key1", "value1")
        self.engine.set("key2", "value2")
        keys = self.engine.keys()
        self.assertEqual(len(keys), 2)
    
    def test_keys_wildcard(self):
        """Test key pattern matching"""
        self.engine.set("user:1", "alice")
        self.engine.set("user:2", "bob")
        self.engine.set("post:1", "hello")
        
        keys = self.engine.keys("user:*")
        self.assertEqual(len(keys), 2)
    
    def test_flush_all(self):
        """Test flushing all keys"""
        self.engine.set("key1", "value1")
        self.engine.set("key2", "value2")
        self.engine.flush_all()
        
        self.assertEqual(len(self.engine.keys()), 0)
    
    def test_info(self):
        """Test getting info"""
        self.engine.set("key1", "value1")
        info = self.engine.info()
        
        self.assertIn("total_keys", info)
        self.assertIn("memory_used", info)
        self.assertEqual(info["total_keys"], 1)
    
    def test_lru_eviction(self):
        """Test LRU eviction when memory full"""
        # Use very small memory: 1.5 KB
        small_engine = StorageEngine(max_memory_mb=0.0015, eviction_policy="lru")
        
        # Add keys (each ~100 bytes)
        for i in range(100):
            small_engine.set(f"key{i}", "x" * 100)
        
        # Only some keys should remain due to memory limit
        self.assertLess(len(small_engine.store), 50)
    
    def test_fifo_eviction(self):
        """Test FIFO eviction when memory full"""
        # Use very small memory: 1.5 KB
        small_engine = StorageEngine(max_memory_mb=0.0015, eviction_policy="fifo")
        
        # Add keys (each ~100 bytes)
        for i in range(100):
            small_engine.set(f"key{i}", "x" * 100)
        
        # Only some keys should remain
        self.assertLess(len(small_engine.store), 50)


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry"""
    
    def test_not_expired(self):
        """Test entry without expiration"""
        entry = CacheEntry("value")
        self.assertFalse(entry.is_expired())
    
    def test_expired(self):
        """Test expired entry"""
        entry = CacheEntry("value", ttl=1)
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
