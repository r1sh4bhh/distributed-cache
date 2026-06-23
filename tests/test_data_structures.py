import unittest
from cache.data_structures import CacheList, CacheHash, CacheSet, DataStructureManager


class TestCacheList(unittest.TestCase):
    """Test CacheList operations"""
    
    def setUp(self):
        self.list = CacheList()
    
    def test_lpush_single(self):
        """Test LPUSH with single value"""
        length = self.list.lpush("a")
        self.assertEqual(length, 1)
        self.assertEqual(self.list.items, ["a"])
    
    def test_lpush_multiple(self):
        """Test LPUSH with multiple values"""
        length = self.list.lpush("c", "b", "a")
        self.assertEqual(length, 3)
        self.assertEqual(self.list.items, ["c", "b", "a"])  # LPUSH adds in order given
    
    def test_rpush(self):
        """Test RPUSH"""
        self.list.rpush("a", "b", "c")
        self.assertEqual(self.list.items, ["a", "b", "c"])
    
    def test_lpop(self):
        """Test LPOP"""
        self.list.rpush("a", "b", "c")
        self.assertEqual(self.list.lpop(), "a")
        self.assertEqual(self.list.items, ["b", "c"])
    
    def test_rpop(self):
        """Test RPOP"""
        self.list.rpush("a", "b", "c")
        self.assertEqual(self.list.rpop(), "c")
        self.assertEqual(self.list.items, ["a", "b"])
    
    def test_llen(self):
        """Test LLEN"""
        self.list.rpush("a", "b", "c")
        self.assertEqual(self.list.llen(), 3)
    
    def test_lrange(self):
        """Test LRANGE"""
        self.list.rpush("a", "b", "c", "d", "e")
        self.assertEqual(self.list.lrange(1, 3), ["b", "c", "d"])
    
    def test_lindex(self):
        """Test LINDEX"""
        self.list.rpush("a", "b", "c")
        self.assertEqual(self.list.lindex(0), "a")
        self.assertEqual(self.list.lindex(2), "c")
        self.assertIsNone(self.list.lindex(5))
    
    def test_lset(self):
        """Test LSET"""
        self.list.rpush("a", "b", "c")
        self.assertTrue(self.list.lset(1, "x"))
        self.assertEqual(self.list.items[1], "x")
    
    def test_ltrim(self):
        """Test LTRIM"""
        self.list.rpush("a", "b", "c", "d", "e")
        self.list.ltrim(1, 3)
        self.assertEqual(self.list.items, ["b", "c", "d"])


class TestCacheHash(unittest.TestCase):
    """Test CacheHash operations"""
    
    def setUp(self):
        self.hash = CacheHash()
    
    def test_hset_new(self):
        """Test HSET on new field"""
        result = self.hash.hset("field1", "value1")
        self.assertEqual(result, 1)
    
    def test_hset_existing(self):
        """Test HSET on existing field"""
        self.hash.hset("field1", "value1")
        result = self.hash.hset("field1", "value2")
        self.assertEqual(result, 0)
    
    def test_hget(self):
        """Test HGET"""
        self.hash.hset("field1", "value1")
        self.assertEqual(self.hash.hget("field1"), "value1")
        self.assertIsNone(self.hash.hget("nonexistent"))
    
    def test_hmget(self):
        """Test HMGET"""
        self.hash.hset("f1", "v1")
        self.hash.hset("f2", "v2")
        result = self.hash.hmget("f1", "f2", "f3")
        self.assertEqual(result, ["v1", "v2", None])
    
    def test_hmset(self):
        """Test HMSET"""
        self.hash.hmset("f1", "v1", "f2", "v2", "f3", "v3")
        self.assertEqual(self.hash.hlen(), 3)
    
    def test_hgetall(self):
        """Test HGETALL"""
        self.hash.hmset("f1", "v1", "f2", "v2")
        result = self.hash.hgetall()
        self.assertEqual(result, {"f1": "v1", "f2": "v2"})
    
    def test_hkeys(self):
        """Test HKEYS"""
        self.hash.hmset("f1", "v1", "f2", "v2")
        keys = self.hash.hkeys()
        self.assertEqual(set(keys), {"f1", "f2"})
    
    def test_hvals(self):
        """Test HVALS"""
        self.hash.hmset("f1", "v1", "f2", "v2")
        vals = self.hash.hvals()
        self.assertEqual(set(vals), {"v1", "v2"})
    
    def test_hlen(self):
        """Test HLEN"""
        self.hash.hmset("f1", "v1", "f2", "v2", "f3", "v3")
        self.assertEqual(self.hash.hlen(), 3)
    
    def test_hdel(self):
        """Test HDEL"""
        self.hash.hmset("f1", "v1", "f2", "v2")
        count = self.hash.hdel("f1", "f3")
        self.assertEqual(count, 1)
        self.assertEqual(self.hash.hlen(), 1)
    
    def test_hincrby(self):
        """Test HINCRBY"""
        self.hash.hset("counter", 10)
        result = self.hash.hincrby("counter", 5)
        self.assertEqual(result, 15)


class TestCacheSet(unittest.TestCase):
    """Test CacheSet operations"""
    
    def setUp(self):
        self.set = CacheSet()
    
    def test_sadd_new(self):
        """Test SADD with new members"""
        count = self.set.sadd("a", "b", "c")
        self.assertEqual(count, 3)
    
    def test_sadd_duplicate(self):
        """Test SADD with duplicate"""
        self.set.sadd("a", "b")
        count = self.set.sadd("a", "c")
        self.assertEqual(count, 1)
    
    def test_smembers(self):
        """Test SMEMBERS"""
        self.set.sadd("a", "b", "c")
        members = set(self.set.smembers())
        self.assertEqual(members, {"a", "b", "c"})
    
    def test_scard(self):
        """Test SCARD"""
        self.set.sadd("a", "b", "c")
        self.assertEqual(self.set.scard(), 3)
    
    def test_sismember_true(self):
        """Test SISMEMBER when member exists"""
        self.set.sadd("a", "b", "c")
        self.assertEqual(self.set.sismember("a"), 1)
    
    def test_sismember_false(self):
        """Test SISMEMBER when member doesn't exist"""
        self.set.sadd("a", "b")
        self.assertEqual(self.set.sismember("c"), 0)
    
    def test_srem(self):
        """Test SREM"""
        self.set.sadd("a", "b", "c")
        count = self.set.srem("a", "d")
        self.assertEqual(count, 1)
        self.assertEqual(self.set.scard(), 2)
    
    def test_sinter(self):
        """Test SINTER (intersection)"""
        set1 = CacheSet()
        set2 = CacheSet()
        set1.sadd("a", "b", "c")
        set2.sadd("b", "c", "d")
        result = set1.sinter(set2)
        self.assertEqual(result, {"b", "c"})
    
    def test_sunion(self):
        """Test SUNION"""
        set1 = CacheSet()
        set2 = CacheSet()
        set1.sadd("a", "b")
        set2.sadd("b", "c")
        result = set1.sunion(set2)
        self.assertEqual(result, {"a", "b", "c"})
    
    def test_sdiff(self):
        """Test SDIFF (difference)"""
        set1 = CacheSet()
        set2 = CacheSet()
        set1.sadd("a", "b", "c")
        set2.sadd("b", "c", "d")
        result = set1.sdiff(set2)
        self.assertEqual(result, {"a"})


class TestDataStructureManager(unittest.TestCase):
    """Test DataStructureManager"""
    
    def setUp(self):
        self.manager = DataStructureManager()
    
    def test_get_list(self):
        """Test getting/creating list"""
        lst = self.manager.get_list("mylist")
        self.assertIsNotNone(lst)
        lst.rpush("a", "b")
        lst2 = self.manager.get_list("mylist")
        self.assertEqual(lst2.llen(), 2)
    
    def test_get_hash(self):
        """Test getting/creating hash"""
        hsh = self.manager.get_hash("myhash")
        hsh.hset("f1", "v1")
        hsh2 = self.manager.get_hash("myhash")
        self.assertEqual(hsh2.hlen(), 1)
    
    def test_get_set(self):
        """Test getting/creating set"""
        st = self.manager.get_set("myset")
        st.sadd("a", "b")
        st2 = self.manager.get_set("myset")
        self.assertEqual(st2.scard(), 2)
    
    def test_delete_list(self):
        """Test deleting list"""
        self.manager.get_list("mylist").rpush("a")
        self.assertTrue(self.manager.delete_list("mylist"))
        self.assertFalse(self.manager.exists_list("mylist"))
    
    def test_flush_all(self):
        """Test flush all"""
        self.manager.get_list("list1").rpush("a")
        self.manager.get_hash("hash1").hset("f", "v")
        self.manager.get_set("set1").sadd("a")
        count = self.manager.flush_all()
        self.assertEqual(count, 3)
        self.assertEqual(len(self.manager.lists), 0)


if __name__ == "__main__":
    unittest.main()