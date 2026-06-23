"""
Data structures for distributed cache
Implements: Lists, Hashes, Sets
"""

from typing import Any, List, Dict, Set, Optional


class CacheList:
    """Redis-like List (doubly-linked list)"""
    
    def __init__(self):
        self.items: List[Any] = []
    
    def lpush(self, *values) -> int:
        """Push values to head of list"""
        for value in reversed(values):
            self.items.insert(0, value)
        return len(self.items)
    
    def rpush(self, *values) -> int:
        """Push values to tail of list"""
        self.items.extend(values)
        return len(self.items)
    
    def lpop(self, count: int = 1) -> Any:
        """Pop from head"""
        if count == 1:
            return self.items.pop(0) if self.items else None
        
        result = []
        for _ in range(min(count, len(self.items))):
            result.append(self.items.pop(0))
        return result if result else None
    
    def rpop(self, count: int = 1) -> Any:
        """Pop from tail"""
        if count == 1:
            return self.items.pop() if self.items else None
        
        result = []
        for _ in range(min(count, len(self.items))):
            result.append(self.items.pop())
        return list(reversed(result)) if result else None
    
    def llen(self) -> int:
        """Get list length"""
        return len(self.items)
    
    def lrange(self, start: int, stop: int) -> List[Any]:
        """Get range of elements"""
        return self.items[start:stop + 1]
    
    def lindex(self, index: int) -> Optional[Any]:
        """Get element at index"""
        try:
            return self.items[index]
        except IndexError:
            return None
    
    def lset(self, index: int, value: Any) -> bool:
        """Set element at index"""
        try:
            self.items[index] = value
            return True
        except IndexError:
            return False
    
    def lrem(self, count: int, value: Any) -> int:
        """Remove elements equal to value"""
        removed = 0
        if count >= 0:
            # Remove from head
            while count > 0 and value in self.items:
                self.items.remove(value)
                removed += 1
                count -= 1
        else:
            # Remove from tail
            count = abs(count)
            while count > 0 and value in self.items:
                self.items.remove(value)
                removed += 1
                count -= 1
        return removed
    
    def ltrim(self, start: int, stop: int) -> bool:
        """Trim list to range"""
        self.items = self.items[start:stop + 1]
        return True


class CacheHash:
    """Redis-like Hash (dictionary)"""
    
    def __init__(self):
        self.fields: Dict[str, Any] = {}
    
    def hset(self, field: str, value: Any) -> int:
        """Set field in hash"""
        is_new = field not in self.fields
        self.fields[field] = value
        return 1 if is_new else 0
    
    def hmset(self, *field_values) -> bool:
        """Set multiple fields"""
        for i in range(0, len(field_values), 2):
            if i + 1 < len(field_values):
                self.fields[field_values[i]] = field_values[i + 1]
        return True
    
    def hget(self, field: str) -> Optional[Any]:
        """Get field value"""
        return self.fields.get(field)
    
    def hmget(self, *fields) -> List[Optional[Any]]:
        """Get multiple field values"""
        return [self.fields.get(field) for field in fields]
    
    def hgetall(self) -> Dict[str, Any]:
        """Get all fields and values"""
        return dict(self.fields)
    
    def hkeys(self) -> List[str]:
        """Get all field names"""
        return list(self.fields.keys())
    
    def hvals(self) -> List[Any]:
        """Get all values"""
        return list(self.fields.values())
    
    def hlen(self) -> int:
        """Get number of fields"""
        return len(self.fields)
    
    def hexists(self, field: str) -> int:
        """Check if field exists"""
        return 1 if field in self.fields else 0
    
    def hdel(self, *fields) -> int:
        """Delete fields"""
        count = 0
        for field in fields:
            if field in self.fields:
                del self.fields[field]
                count += 1
        return count
    
    def hincrby(self, field: str, increment: int) -> int:
        """Increment field value"""
        current = self.fields.get(field, 0)
        new_value = current + increment
        self.fields[field] = new_value
        return new_value
    
    def hincrbyfloat(self, field: str, increment: float) -> float:
        """Increment field by float"""
        current = float(self.fields.get(field, 0))
        new_value = current + increment
        self.fields[field] = new_value
        return new_value


class CacheSet:
    """Redis-like Set (unique collection)"""
    
    def __init__(self):
        self.members: Set[Any] = set()
    
    def sadd(self, *members) -> int:
        """Add members to set"""
        count = 0
        for member in members:
            if member not in self.members:
                self.members.add(member)
                count += 1
        return count
    
    def srem(self, *members) -> int:
        """Remove members from set"""
        count = 0
        for member in members:
            if member in self.members:
                self.members.remove(member)
                count += 1
        return count
    
    def smembers(self) -> List[Any]:
        """Get all members"""
        return list(self.members)
    
    def scard(self) -> int:
        """Get set cardinality (size)"""
        return len(self.members)
    
    def sismember(self, member: Any) -> int:
        """Check if member exists"""
        return 1 if member in self.members else 0
    
    def spop(self, count: int = 1) -> Any:
        """Pop random members"""
        if not self.members:
            return None
        
        if count == 1:
            member = self.members.pop()
            self.members.add(member)  # Don't actually remove for now
            return member
        
        import random
        result = random.sample(list(self.members), min(count, len(self.members)))
        return result
    
    def srandmember(self, count: int = 1) -> Any:
        """Get random members (without removing)"""
        if not self.members:
            return None
        
        import random
        if count == 1:
            return random.choice(list(self.members))
        
        return random.sample(list(self.members), min(count, len(self.members)))
    
    def sinter(self, *other_sets) -> Set[Any]:
        """Intersection of sets"""
        result = self.members.copy()
        for other in other_sets:
            if isinstance(other, CacheSet):
                result = result.intersection(other.members)
        return result
    
    def sunion(self, *other_sets) -> Set[Any]:
        """Union of sets"""
        result = self.members.copy()
        for other in other_sets:
            if isinstance(other, CacheSet):
                result = result.union(other.members)
        return result
    
    def sdiff(self, *other_sets) -> Set[Any]:
        """Difference of sets"""
        result = self.members.copy()
        for other in other_sets:
            if isinstance(other, CacheSet):
                result = result.difference(other.members)
        return result


class DataStructureManager:
    """Manage all data structures in cache"""
    
    def __init__(self):
        self.lists: Dict[str, CacheList] = {}
        self.hashes: Dict[str, CacheHash] = {}
        self.sets: Dict[str, CacheSet] = {}
    
    def get_list(self, key: str) -> CacheList:
        """Get or create list"""
        if key not in self.lists:
            self.lists[key] = CacheList()
        return self.lists[key]
    
    def get_hash(self, key: str) -> CacheHash:
        """Get or create hash"""
        if key not in self.hashes:
            self.hashes[key] = CacheHash()
        return self.hashes[key]
    
    def get_set(self, key: str) -> CacheSet:
        """Get or create set"""
        if key not in self.sets:
            self.sets[key] = CacheSet()
        return self.sets[key]
    
    def delete_list(self, key: str) -> bool:
        """Delete list"""
        if key in self.lists:
            del self.lists[key]
            return True
        return False
    
    def delete_hash(self, key: str) -> bool:
        """Delete hash"""
        if key in self.hashes:
            del self.hashes[key]
            return True
        return False
    
    def delete_set(self, key: str) -> bool:
        """Delete set"""
        if key in self.sets:
            del self.sets[key]
            return True
        return False
    
    def exists_list(self, key: str) -> bool:
        """Check if list exists"""
        return key in self.lists
    
    def exists_hash(self, key: str) -> bool:
        """Check if hash exists"""
        return key in self.hashes
    
    def exists_set(self, key: str) -> bool:
        """Check if set exists"""
        return key in self.sets
    
    def flush_all(self) -> int:
        """Delete all data structures"""
        count = len(self.lists) + len(self.hashes) + len(self.sets)
        self.lists.clear()
        self.hashes.clear()
        self.sets.clear()
        return count
