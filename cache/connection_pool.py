"""
Connection pooling for distributed cache
Manages client connections efficiently
"""

import socket
import threading
from typing import Optional, Dict, List
from queue import Queue, Empty


class Connection:
    """Represents a single connection"""
    
    def __init__(self, socket_obj: socket.socket, conn_id: int):
        self.socket = socket_obj
        self.conn_id = conn_id
        self.in_use = False
        self.created_at = None
        self.last_used = None
        self.request_count = 0
    
    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if connection is stale"""
        if not self.last_used:
            return False
        
        import time
        return time.time() - self.last_used > timeout_seconds
    
    def mark_used(self):
        """Mark connection as used"""
        import time
        self.last_used = time.time()
        self.request_count += 1
    
    def close(self):
        """Close connection"""
        try:
            self.socket.close()
        except:
            pass


class ConnectionPool:
    """Connection pool for managing client connections"""
    
    def __init__(self, max_connections: int = 100, timeout: int = 300):
        self.max_connections = max_connections
        self.timeout = timeout
        self.available: Queue = Queue()
        self.in_use: Dict[int, Connection] = {}
        self.all_connections: Dict[int, Connection] = {}
        self.next_conn_id = 0
        self.lock = threading.Lock()
    
    def acquire(self, socket_obj: socket.socket) -> int:
        """Acquire a connection"""
        with self.lock:
            # Reuse available connection if exists
            try:
                conn = self.available.get_nowait()
                if not conn.is_stale(self.timeout):
                    conn.in_use = True
                    self.in_use[conn.conn_id] = conn
                    return conn.conn_id
                else:
                    conn.close()
            except Empty:
                pass
            
            # Create new connection if under limit
            if len(self.all_connections) < self.max_connections:
                conn = Connection(socket_obj, self.next_conn_id)
                conn.in_use = True
                conn.created_at = __import__('time').time()
                conn.mark_used()
                
                self.all_connections[self.next_conn_id] = conn
                self.in_use[self.next_conn_id] = conn
                self.next_conn_id += 1
                
                return conn.conn_id
        
        return -1
    
    def release(self, conn_id: int):
        """Release a connection back to pool"""
        with self.lock:
            if conn_id in self.in_use:
                conn = self.in_use.pop(conn_id)
                conn.in_use = False
                conn.mark_used()
                
                if not conn.is_stale(self.timeout):
                    self.available.put(conn)
                else:
                    conn.close()
                    del self.all_connections[conn_id]
    
    def get_connection(self, conn_id: int) -> Optional[Connection]:
        """Get connection by ID"""
        return self.all_connections.get(conn_id)
    
    def close_all(self):
        """Close all connections"""
        with self.lock:
            for conn in self.all_connections.values():
                conn.close()
            self.all_connections.clear()
            self.in_use.clear()
            
            # Empty queue
            while not self.available.empty():
                try:
                    self.available.get_nowait()
                except Empty:
                    break
    
    def get_stats(self) -> dict:
        """Get pool statistics"""
        with self.lock:
            return {
                "total_connections": len(self.all_connections),
                "in_use": len(self.in_use),
                "available": self.available.qsize(),
                "max_connections": self.max_connections,
                "requests": sum(c.request_count for c in self.all_connections.values())
            }
