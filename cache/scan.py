"""
SCAN command for iterating cache keys
Implements: SCAN, HSCAN, SSCAN, LSCAN
"""

from typing import List, Tuple, Optional
import fnmatch


class ScanCursor:
    """Manages scan cursor state"""
    
    def __init__(self, items: List, pattern: str = "*", count: int = 10):
        self.items = list(items)
        self.pattern = pattern
        self.count = count
        self.position = 0
        
        # Filter by pattern
        self.filtered = [item for item in self.items if fnmatch.fnmatch(str(item), pattern)]
    
    def scan(self, cursor: int = 0) -> Tuple[int, List]:
        """
        Scan with cursor
        Returns: (next_cursor, items)
        """
        start = cursor
        end = min(cursor + self.count, len(self.filtered))
        
        items = self.filtered[start:end]
        
        # Calculate next cursor
        if end >= len(self.filtered):
            next_cursor = 0
        else:
            next_cursor = end
        
        return next_cursor, items


class ScanManager:
    """Manages SCAN operations across data structures"""
    
    def __init__(self):
        self.cursors = {}  # cursor_id -> ScanCursor
        self.next_cursor_id = 1
    
    def scan_keys(self, storage, cursor: int = 0, pattern: str = "*", count: int = 10) -> Tuple[int, List]:
        """SCAN - iterate string keys"""
        keys = storage.store.keys()
        cursor_obj = ScanCursor(list(keys), pattern, count)
        next_cursor, items = cursor_obj.scan(cursor)
        return next_cursor, items
    
    def scan_hash(self, hash_obj, cursor: int = 0, pattern: str = "*", count: int = 10) -> Tuple[int, List]:
        """HSCAN - iterate hash fields"""
        fields = hash_obj.fields.keys()
        cursor_obj = ScanCursor(list(fields), pattern, count)
        next_cursor, items = cursor_obj.scan(cursor)
        
        # Return as field-value pairs
        result = []
        for field in items:
            result.append(field)
            result.append(hash_obj.fields[field])
        
        return next_cursor, result
    
    def scan_set(self, set_obj, cursor: int = 0, pattern: str = "*", count: int = 10) -> Tuple[int, List]:
        """SSCAN - iterate set members"""
        members = set_obj.members
        cursor_obj = ScanCursor(list(members), pattern, count)
        next_cursor, items = cursor_obj.scan(cursor)
        return next_cursor, items
    
    def scan_list(self, list_obj, cursor: int = 0, pattern: str = "*", count: int = 10) -> Tuple[int, List]:
        """LSCAN - iterate list elements"""
        items = list_obj.items
        cursor_obj = ScanCursor(items, pattern, count)
        next_cursor, items = cursor_obj.scan(cursor)
        return next_cursor, items
