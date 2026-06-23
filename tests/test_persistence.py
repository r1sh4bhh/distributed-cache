import unittest
import time
import os
from cache.persistence import RDBPersistence, AOFPersistence, PersistenceManager
from cache.storage import StorageEngine, CacheEntry


class TestRDBPersistence(unittest.TestCase):
    """Test RDB persistence"""
    
    def setUp(self):
        """Create fresh RDB for each test"""
        self.rdb = RDBPersistence("test_cache.rdb")
        # Clean up if exists
        if self.rdb.exists():
            self.rdb.remove()
    
    def tearDown(self):
        """Clean up test files"""
        if self.rdb.exists():
            self.rdb.remove()
    
    def test_save_and_load(self):
        """Test saving and loading cache"""
        # Create entries
        store = {
            "key1": CacheEntry("value1"),
            "key2": CacheEntry("value2", ttl=3600)
        }
        
        # Save
        self.assertTrue(self.rdb.save(store))
        self.assertTrue(self.rdb.exists())
        
        # Load
        loaded = self.rdb.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded), 2)
        self.assertIn("key1", loaded)
        self.assertIn("key2", loaded)
    
    def test_load_nonexistent(self):
        """Test loading non-existent RDB"""
        self.assertIsNone(self.rdb.load())
    
    def test_atomic_save(self):
        """Test atomic save (temp file rename)"""
        store = {"key": CacheEntry("value")}
        
        # Save multiple times
        for i in range(10):
            self.assertTrue(self.rdb.save(store))
        
        # Should still be valid
        loaded = self.rdb.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded), 1)


class TestAOFPersistence(unittest.TestCase):
    """Test AOF persistence"""
    
    def setUp(self):
        """Create fresh AOF for each test"""
        self.aof = AOFPersistence("test_cache.aof")
        if os.path.exists(self.aof.filepath):
            os.remove(self.aof.filepath)
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.aof.filepath):
            os.remove(self.aof.filepath)
    
    def test_log_and_replay(self):
        """Test logging and replaying commands"""
        # Log commands
        self.aof.log_command("SET", ["key1", "value1"])
        self.aof.log_command("SET", ["key2", "value2", "3600"])
        self.aof.log_command("DEL", ["key1"])
        
        # Replay
        commands = self.aof.replay()
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[0], ("SET", ["key1", "value1"]))
        self.assertEqual(commands[1], ("SET", ["key2", "value2", "3600"]))
        self.assertEqual(commands[2], ("DEL", ["key1"]))
    
    def test_rewrite(self):
        """Test AOF rewrite"""
        # Create store
        store = {
            "key1": CacheEntry("value1"),
            "key2": CacheEntry("value2", ttl=3600)
        }
        
        # Rewrite
        self.assertTrue(self.aof.rewrite(store))
        
        # File should exist
        self.assertTrue(os.path.exists(self.aof.filepath))
        
        # Should be readable
        commands = self.aof.replay()
        self.assertGreaterEqual(len(commands), 2)
    
    def test_should_rewrite(self):
        """Test rewrite decision logic"""
        self.assertFalse(self.aof.should_rewrite())
        
        # Create large file
        self.aof.file_size = 11 * 1024 * 1024  # 11MB
        self.assertTrue(self.aof.should_rewrite())


class TestPersistenceManager(unittest.TestCase):
    """Test PersistenceManager"""
    
    def setUp(self):
        """Create fresh manager for each test"""
        self.manager = PersistenceManager(
            rdb_enabled=True,
            aof_enabled=True,
            rdb_file="test_cache.rdb",
            aof_file="test_cache.aof"
        )
        # Clean up
        if os.path.exists("test_cache.rdb"):
            os.remove("test_cache.rdb")
        if os.path.exists("test_cache.aof"):
            os.remove("test_cache.aof")
    
    def tearDown(self):
        """Clean up test files"""
        self.manager.cleanup()
    
    def test_restore_empty(self):
        """Test restore with no persistence"""
        self.assertIsNone(self.manager.restore())
    
    def test_save_and_restore(self):
        """Test save and restore"""
        store = {
            "key1": CacheEntry("value1"),
            "key2": CacheEntry("value2", ttl=3600)
        }
        
        # Save RDB
        self.assertTrue(self.manager.save_snapshot(store))
        
        # Restore
        restored = self.manager.restore()
        self.assertIsNotNone(restored)
        self.assertEqual(len(restored), 2)
    
    def test_log_and_restore_aof(self):
        """Test AOF logging and restore"""
        # Log commands
        self.manager.log_command("SET", ["key1", "value1"])
        self.manager.log_command("SET", ["key2", "value2"])
        
        # Delete RDB so it uses AOF
        if os.path.exists("test_cache.rdb"):
            os.remove("test_cache.rdb")
        
        # Restore from AOF
        restored = self.manager.restore()
        self.assertIsNotNone(restored)
        self.assertGreaterEqual(len(restored), 2)
    
    def test_persistence_stats(self):
        """Test get_stats"""
        store = {"key": CacheEntry("value")}
        self.manager.save_snapshot(store)
        self.manager.log_command("SET", ["key", "value"])
        
        stats = self.manager.get_stats()
        self.assertIn("rdb", stats)
        self.assertIn("aof", stats)
        self.assertTrue(stats["rdb"]["enabled"])
        self.assertTrue(stats["aof"]["enabled"])


class TestPersistenceIntegration(unittest.TestCase):
    """Integration tests with StorageEngine"""
    
    def setUp(self):
        """Create storage with persistence"""
        self.manager = PersistenceManager(
            rdb_enabled=True,
            aof_enabled=True,
            rdb_file="test_integration.rdb",
            aof_file="test_integration.aof"
        )
        self.storage = StorageEngine(persistence=self.manager)
        
        # Clean up
        self.manager.cleanup()
    
    def tearDown(self):
        """Clean up"""
        self.manager.cleanup()
    
    def test_set_and_persist(self):
        """Test SET with persistence logging"""
        # Set values
        self.storage.set("key1", "value1")
        self.storage.set("key2", "value2", ttl=3600)
        
        # Save
        self.manager.save_snapshot(self.storage.store)
        
        # Verify files exist
        self.assertTrue(self.manager.rdb.exists())
    
    def test_recovery(self):
        """Test recovering from disk"""
        # Store some data
        self.storage.set("key1", "value1")
        self.storage.set("key2", "value2")
        
        # Save
        self.manager.save_snapshot(self.storage.store)
        
        # Create new storage and restore
        manager2 = PersistenceManager(
            rdb_enabled=True,
            aof_enabled=False,
            rdb_file="test_integration.rdb"
        )
        restored = manager2.restore()
        
        self.assertIsNotNone(restored)
        self.assertEqual(len(restored), 2)
        self.assertIn("key1", restored)
        self.assertIn("key2", restored)


if __name__ == "__main__":
    unittest.main()
