import unittest
import socket
from cache.connection_pool import Connection, ConnectionPool
from cache.pipelining import Pipeline, PipelineProcessor, PipelineClient
from cache.async_io import AsyncRequest, AsyncWorker, AsyncClient


class TestConnection(unittest.TestCase):
    """Test Connection"""
    
    def setUp(self):
        # Create a mock socket
        self.mock_socket = socket.socket()
        self.connection = Connection(self.mock_socket, 1)
    
    def tearDown(self):
        try:
            self.mock_socket.close()
        except:
            pass
    
    def test_creation(self):
        """Test creating connection"""
        self.assertEqual(self.connection.conn_id, 1)
        self.assertFalse(self.connection.in_use)
    
    def test_mark_used(self):
        """Test marking connection as used"""
        self.connection.mark_used()
        self.assertEqual(self.connection.request_count, 1)
        
        self.connection.mark_used()
        self.assertEqual(self.connection.request_count, 2)


class TestConnectionPool(unittest.TestCase):
    """Test ConnectionPool"""
    
    def setUp(self):
        self.pool = ConnectionPool(max_connections=5)
    
    def tearDown(self):
        self.pool.close_all()
    
    def test_acquire(self):
        """Test acquiring connection"""
        mock_socket = socket.socket()
        conn_id = self.pool.acquire(mock_socket)
        self.assertGreaterEqual(conn_id, 0)
    
    def test_release(self):
        """Test releasing connection"""
        mock_socket = socket.socket()
        conn_id = self.pool.acquire(mock_socket)
        self.pool.release(conn_id)
        
        conn = self.pool.get_connection(conn_id)
        self.assertIsNotNone(conn)
        self.assertFalse(conn.in_use)
    
    def test_max_connections(self):
        """Test max connections limit"""
        for i in range(5):
            mock_socket = socket.socket()
            self.pool.acquire(mock_socket)
        
        # Next acquire should return -1 (pool full)
        mock_socket = socket.socket()
        conn_id = self.pool.acquire(mock_socket)
        self.assertEqual(conn_id, -1)
    
    def test_get_stats(self):
        """Test pool statistics"""
        stats = self.pool.get_stats()
        self.assertIn("total_connections", stats)
        self.assertIn("in_use", stats)
        self.assertIn("available", stats)


class TestPipeline(unittest.TestCase):
    """Test Pipeline"""
    
    def setUp(self):
        self.pipeline = Pipeline()
    
    def test_add_command(self):
        """Test adding commands"""
        self.pipeline.add_command("SET", "key1", "value1")
        self.pipeline.add_command("GET", "key1")
        
        self.assertEqual(self.pipeline.size(), 2)
    
    def test_get_request(self):
        """Test getting RESP request"""
        self.pipeline.add_command("SET", "key", "value")
        request = self.pipeline.get_request()
        
        self.assertIsNotNone(request)
        self.assertIn(b"SET", request)
    
    def test_clear(self):
        """Test clearing pipeline"""
        self.pipeline.add_command("SET", "key", "value")
        self.pipeline.clear()
        
        self.assertEqual(self.pipeline.size(), 0)


class TestPipelineProcessor(unittest.TestCase):
    """Test PipelineProcessor"""
    
    def test_parse_simple_string(self):
        """Test parsing simple string response"""
        data = b"+OK\r\n"
        response, bytes_read = PipelineProcessor._parse_single_response(data)
        self.assertEqual(response, "OK")
    
    def test_parse_integer(self):
        """Test parsing integer response"""
        data = b":100\r\n"
        response, bytes_read = PipelineProcessor._parse_single_response(data)
        self.assertEqual(response, 100)
    
    def test_parse_bulk_string(self):
        """Test parsing bulk string"""
        data = b"$5\r\nhello\r\n"
        response, bytes_read = PipelineProcessor._parse_single_response(data)
        self.assertEqual(response, "hello")
    
    def test_parse_null_bulk_string(self):
        """Test parsing null bulk string"""
        data = b"$-1\r\n"
        response, bytes_read = PipelineProcessor._parse_single_response(data)
        self.assertIsNone(response)
    
    def test_parse_array(self):
        """Test parsing array"""
        data = b"*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
        response, bytes_read = PipelineProcessor._parse_single_response(data)
        self.assertEqual(response, ["foo", "bar"])


class TestAsyncRequest(unittest.TestCase):
    """Test AsyncRequest"""
    
    def test_creation(self):
        """Test creating async request"""
        def callback(result):
            pass
        
        request = AsyncRequest("SET", ["key", "value"], callback)
        self.assertEqual(request.command, "SET")
        self.assertFalse(request.done)
    
    def test_completion(self):
        """Test marking request as done"""
        request = AsyncRequest("SET", ["key", "value"], None)
        request.result = "OK"
        request.done = True
        
        self.assertTrue(request.done)
        self.assertEqual(request.result, "OK")


if __name__ == "__main__":
    unittest.main()
