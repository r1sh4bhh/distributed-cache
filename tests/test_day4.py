import unittest
from cache.transactions import Transaction, TransactionManager
from cache.bit_operations import BitField, BitOperationManager
from cache.scan import ScanCursor, ScanManager
from cache.storage import StorageEngine


class TestTransaction(unittest.TestCase):
    """Test Transaction"""
    
    def setUp(self):
        self.transaction = Transaction()
    
    def test_queue_command(self):
        """Test queuing commands"""
        self.transaction.queue_command("SET", ["key1", "value1"])
        self.transaction.queue_command("GET", ["key1"])
        self.assertEqual(len(self.transaction.commands), 2)
    
    def test_discard(self):
        """Test discarding transaction"""
        self.transaction.queue_command("SET", ["key1", "value1"])
        self.transaction.discard()
        self.assertEqual(len(self.transaction.commands), 0)


class TestTransactionManager(unittest.TestCase):
    """Test TransactionManager"""
    
    def setUp(self):
        self.manager = TransactionManager()
    
    def test_start_transaction(self):
        """Test starting transaction"""
        self.assertTrue(self.manager.start_transaction("client1"))
        self.assertFalse(self.manager.start_transaction("client1"))  # Already in transaction
    
    def test_queue_command(self):
        """Test queueing in transaction"""
        self.manager.start_transaction("client1")
        self.assertTrue(self.manager.queue_command("client1", "SET", ["key", "value"]))
    
    def test_discard_transaction(self):
        """Test discarding transaction"""
        self.manager.start_transaction("client1")
        self.manager.queue_command("client1", "SET", ["key", "value"])
        self.assertTrue(self.manager.discard_transaction("client1"))
        self.assertFalse(self.manager.in_transaction("client1"))


class TestBitField(unittest.TestCase):
    """Test BitField operations"""
    
    def setUp(self):
        self.bf = BitField("A")  # 'A' = 0x41 = 01000001
    
    def test_setbit(self):
        """Test SETBIT"""
        old = self.bf.setbit(0, 1)
        self.assertEqual(old, 0)
        self.assertEqual(self.bf.getbit(0), 1)
    
    def test_getbit(self):
        """Test GETBIT"""
        # 'A' = 01000001, so bit 1 should be 1
        self.assertEqual(self.bf.getbit(1), 1)
        # Bit 2 should be 0
        self.assertEqual(self.bf.getbit(2), 0)
    
    def test_bitcount(self):
        """Test BITCOUNT"""
        # 'A' = 01000001 = 2 bits set
        count = self.bf.bitcount()
        self.assertEqual(count, 2)
    
    def test_bitpos(self):
        """Test BITPOS"""
        # First 0 bit in 'A' (01000001) is at position 0
        pos = self.bf.bitpos(0)
        self.assertEqual(pos, 0)
    
    def test_get_value(self):
        """Test getting value back"""
        bf = BitField("hello")
        self.assertEqual(bf.get_value(), "hello")


class TestBitOperationManager(unittest.TestCase):
    """Test bit operations"""
    
    def setUp(self):
        self.storage = StorageEngine()
        self.manager = BitOperationManager()
    
    def test_bitop_and(self):
        """Test BITOP AND"""
        self.storage.set("key1", "foo")
        self.storage.set("key2", "bar")
        
        result = self.manager.bitop("AND", "dest", "key1", "key2", storage=self.storage)
        self.assertGreater(result, 0)
    
    def test_bitop_or(self):
        """Test BITOP OR"""
        self.storage.set("key1", "foo")
        self.storage.set("key2", "bar")
        
        result = self.manager.bitop("OR", "dest", "key1", "key2", storage=self.storage)
        self.assertGreater(result, 0)


class TestScanCursor(unittest.TestCase):
    """Test SCAN cursor"""
    
    def setUp(self):
        items = ["key1", "key2", "key3", "key4", "key5"]
        self.cursor = ScanCursor(items, "*", 2)
    
    def test_scan_first(self):
        """Test first scan"""
        next_cursor, items = self.cursor.scan(0)
        self.assertEqual(len(items), 2)
        self.assertGreater(next_cursor, 0)
    
    def test_scan_pattern(self):
        """Test scan with pattern"""
        items = ["user:1", "user:2", "post:1", "post:2"]
        cursor = ScanCursor(items, "user:*", 10)
        next_cursor, results = cursor.scan(0)
        self.assertEqual(len(results), 2)


class TestScanManager(unittest.TestCase):
    """Test ScanManager"""
    
    def setUp(self):
        self.storage = StorageEngine()
        self.manager = ScanManager()
        
        # Add some keys
        for i in range(5):
            self.storage.set(f"key{i}", f"value{i}")
    
    def test_scan_keys(self):
        """Test SCAN keys"""
        next_cursor, items = self.manager.scan_keys(self.storage, 0, "*", 2)
        self.assertEqual(len(items), 2)
    
    def test_scan_with_pattern(self):
        """Test SCAN with pattern"""
        next_cursor, items = self.manager.scan_keys(self.storage, 0, "key1", 10)
        self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
